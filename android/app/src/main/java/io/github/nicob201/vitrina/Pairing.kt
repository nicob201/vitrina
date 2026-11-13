package io.github.nicob201.vitrina

import java.security.MessageDigest

/** What `python3 server.py pair` hands over: the key, the certificate's SHA-256 and where to find the Mac. */
data class PairingInfo(val key: String, val fingerprint: String, val port: Int, val wifiIp: String) {
    override fun toString() = "PairingInfo(fingerprint=$fingerprint, port=$port, wifiIp=$wifiIp)" // never the key
}

object Pairing {
    private val KEY = Regex("^[A-Za-z0-9_-]{32,128}$")
    private val FINGERPRINT = Regex("^[0-9a-f]{64}$")
    private val IPV4_PART = Regex("^(0|[1-9][0-9]{0,2})$")

    /** Everything is checked: this arrives from outside the app. Anything off → null. */
    fun parse(key: String?, fingerprint: String?, port: Int, wifiIp: String?): PairingInfo? {
        if (key == null || !KEY.matches(key)) return null
        if (fingerprint == null || !FINGERPRINT.matches(fingerprint)) return null
        if (port !in 1..65535) return null
        val ip = wifiIp ?: ""
        if (ip.isNotEmpty() && !isIpv4(ip)) return null
        return PairingInfo(key, fingerprint, port, ip)
    }

    /** A literal address only: names are never resolved, so nothing can redirect the app elsewhere. */
    fun isIpv4(s: String): Boolean {
        val parts = s.split(".")
        return parts.size == 4 && parts.all { IPV4_PART.matches(it) && it.toInt() <= 255 }
    }

    fun fingerprintOf(certDer: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(certDer).joinToString("") { "%02x".format(it) }

    fun matches(certDer: ByteArray, expected: String): Boolean =
        MessageDigest.isEqual(fingerprintOf(certDer).toByteArray(), expected.toByteArray())

    /** Cable (through `adb reverse`) first, then WiFi. */
    fun origins(info: PairingInfo): List<String> =
        listOfNotNull("https://localhost:${info.port}", info.wifiIp.takeIf { it.isNotEmpty() }?.let { "https://$it:${info.port}" })
}
