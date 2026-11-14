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

/**
 * HTTPS to the paired Mac only: its certificate is recognized by fingerprint, nothing else is trusted, and
 * the key travels as a Bearer header. Everything the app and its page ask the Mac goes through here.
 */
object PinnedClient {
    /** The server answered with a certificate that is not the paired one. */
    const val WRONG_CERT = -2

    /** HTTP status, [WRONG_CERT], or -1 when the Mac can't be reached. */
    fun get(origin: String, path: String, info: PairingInfo, timeoutMs: Int = 5000): Int {
        val trust = PinnedTrust(info.fingerprint)
        var conn: HttpsURLConnection? = null
        return try {
            conn = connect(origin + path, info, trust, emptyMap(), timeoutMs, timeoutMs)
            conn.responseCode
        } catch (e: IOException) {
            if (trust.mismatch) WRONG_CERT else -1
        } finally {
            conn?.disconnect()
        }
    }

    /** A GET whose status line has been read; the caller reads (and so closes) the body. */
    fun open(url: String, info: PairingInfo, headers: Map<String, String>, readTimeoutMs: Int): HttpsURLConnection =
        connect(url, info, PinnedTrust(info.fingerprint), headers, 5000, readTimeoutMs).also { it.responseCode }

    /** "text/css; charset=utf-8" → ("text/css", "utf-8"). */
    fun contentType(header: String?): Pair<String, String?> {
        val parts = header.orEmpty().split(";").map { it.trim() }
        val mime = parts.first().ifEmpty { "application/octet-stream" }
        val charset = parts.drop(1).firstOrNull { it.startsWith("charset=", ignoreCase = true) }
            ?.substringAfter("=")?.trim('"')
        return mime to charset
    }

    private fun connect(
        url: String, info: PairingInfo, trust: PinnedTrust, headers: Map<String, String>, connectMs: Int, readMs: Int,
    ): HttpsURLConnection {
        val tls = SSLContext.getInstance("TLS").apply { init(null, arrayOf(trust), SecureRandom()) }
        return (URL(url).openConnection() as HttpsURLConnection).apply {
            sslSocketFactory = tls.socketFactory
            hostnameVerifier = HostnameVerifier { _, _ -> true } // the fingerprint replaces the name check
            connectTimeout = connectMs
            readTimeout = readMs
            instanceFollowRedirects = false // the key never follows a redirect
            useCaches = false
            for ((k, v) in headers) setRequestProperty(k, v)
            setRequestProperty("Authorization", "Bearer ${info.key}")
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
