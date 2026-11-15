package io.github.nicob201.vitrina

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class PairingTest {
    private val key = "Zq3_x-Y8kLm2Pn4Rs6Tv8Wx0Yz1Ab3Cd5Ef7Gh9Ij0K" // 43 chars, like secrets.token_urlsafe(32)
    private val fp = "07074e2553f7d46c9b5293b5e997337a13be963d0071620ab83080fd45ad4bae"
    private val abcFp = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" // SHA-256("abc")

    @Test fun validPairing() {
        val info = Pairing.parse(key, fp, 8765, "192.168.0.10")
        assertEquals(PairingInfo(key, fp, 8765, "192.168.0.10"), info)
    }

    @Test fun invalidFieldsAreRejected() {
        val cases = listOf(
            listOf(null, fp, 8765, ""),
            listOf("short", fp, 8765, ""),
            listOf(key.dropLast(12), fp, 8765, ""),          // 31 chars
            listOf("$key with spaces", fp, 8765, ""),
            listOf("$key;rm", fp, 8765, ""),
            listOf(key.repeat(4), fp, 8765, ""),             // absurdly long
            listOf(key, null, 8765, ""),
            listOf(key, fp.uppercase(), 8765, ""),
            listOf(key, fp.dropLast(1), 8765, ""),
            listOf(key, fp + "0", 8765, ""),
            listOf(key, fp, 0, ""),
            listOf(key, fp, 70000, ""),
            listOf(key, fp, 8765, "192.168.0.256"),
            listOf(key, fp, 8765, "mac.local"),
        )
        for (c in cases) {
            assertNull("$c", Pairing.parse(c[0] as String?, c[1] as String?, c[2] as Int, c[3] as String?))
        }
    }

    @Test fun ipv4Literals() {
        for (ok in listOf("0.0.0.0", "10.0.0.1", "192.168.1.20", "255.255.255.255")) assertTrue(ok, Pairing.isIpv4(ok))
        for (bad in listOf("", "1.2.3", "1.2.3.4.5", "1.2.3.256", "1.2.3.-1", " 1.2.3.4", "1.2.3.4 ", "01.2.3.4",
                "1..3.4", "a.b.c.d", "١.٢.٣.٤", "1.2.3.4/24", "localhost")) assertFalse(bad, Pairing.isIpv4(bad))
    }

    @Test fun emptyOrMissingWifiIpMeansCableOnly() {
        assertEquals(listOf("https://localhost:8765"), Pairing.origins(Pairing.parse(key, fp, 8765, "")!!))
        assertEquals(listOf("https://localhost:8765"), Pairing.origins(Pairing.parse(key, fp, 8765, null)!!))
    }

    @Test fun originsTryTheCableFirst() {
        assertEquals(listOf("https://localhost:8765", "https://192.168.0.10:8765"),
            Pairing.origins(Pairing.parse(key, fp, 8765, "192.168.0.10")!!))
    }

    @Test fun onlyThePairedOriginsArePaired() {
        val info = Pairing.parse(key, fp, 8765, "192.168.0.10")!!
        for (ok in listOf("https://localhost:8765/", "https://192.168.0.10:8765/a.css?v=2", "HTTPS://LOCALHOST:8765/api/state"))
            assertTrue(ok, Pairing.isPaired(ok, info))
        for (bad in listOf("http://192.168.0.10:8765/", "https://192.168.0.10:8766/", "https://192.168.0.10/",
                "https://192.168.0.10:8765@evil.example/", "https://evil.example:8765/", "https://192.168.0.11:8765/",
                "javascript:alert(1)", "about:blank", "data:text/html,x", "not a url", ""))
            assertFalse(bad, Pairing.isPaired(bad, info))
    }

    @Test fun fingerprintOfKnownBytes() = assertEquals(abcFp, Pairing.fingerprintOf("abc".toByteArray()))

    @Test fun matchesOnlyTheSameCert() {
        assertTrue(Pairing.matches("abc".toByteArray(), abcFp))
        assertFalse(Pairing.matches("abd".toByteArray(), abcFp))
        assertFalse(Pairing.matches("abc".toByteArray(), abcFp.uppercase()))
        assertFalse(Pairing.matches("abc".toByteArray(), ""))
    }

    @Test fun keyIsNotInToString() {
        val info = Pairing.parse(key, fp, 8765, "")
        assertNotNull(info)
        assertFalse(info.toString().contains(key))
    }
}
