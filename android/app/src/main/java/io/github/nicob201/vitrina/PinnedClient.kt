package io.github.nicob201.vitrina

import java.io.IOException
import java.net.URL
import java.security.SecureRandom
import java.security.cert.CertificateException
import java.security.cert.X509Certificate
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.HttpsURLConnection
import javax.net.ssl.SSLContext
import javax.net.ssl.X509TrustManager

/** HTTPS to the paired Mac only: its certificate is recognized by fingerprint, nothing else is trusted. */
object PinnedClient {
    /** The server answered with a certificate that is not the paired one. */
    const val WRONG_CERT = -2

    /** HTTP status, [WRONG_CERT], or -1 when the Mac can't be reached. */
    fun get(origin: String, path: String, info: PairingInfo, timeoutMs: Int = 5000): Int {
        val trust = PinnedTrust(info.fingerprint)
        var conn: HttpsURLConnection? = null
        return try {
            val tls = SSLContext.getInstance("TLS").apply { init(null, arrayOf(trust), SecureRandom()) }
            conn = (URL(origin + path).openConnection() as HttpsURLConnection).apply {
                sslSocketFactory = tls.socketFactory
                hostnameVerifier = HostnameVerifier { _, _ -> true } // the fingerprint replaces the name check
                connectTimeout = timeoutMs
                readTimeout = timeoutMs
                instanceFollowRedirects = false // the key never follows a redirect
                useCaches = false
                setRequestProperty("Authorization", "Bearer ${info.key}")
            }
            conn.responseCode
        } catch (e: IOException) {
            if (trust.mismatch) WRONG_CERT else -1
        } finally {
            conn?.disconnect()
        }
    }

    private class PinnedTrust(private val fingerprint: String) : X509TrustManager {
        @Volatile var mismatch = false

        override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String) {
            if (chain.isEmpty() || !Pairing.matches(chain[0].encoded, fingerprint)) {
                mismatch = true
                throw CertificateException("not the paired certificate")
            }
        }

        override fun checkClientTrusted(chain: Array<X509Certificate>, authType: String) =
            throw CertificateException("no client certificates")

        override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
    }
}
