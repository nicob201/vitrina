package io.github.nicob201.vitrina

import org.junit.Assert.assertEquals
import org.junit.Test

class PinnedClientTest {
    @Test fun contentTypeSplitsMimeAndCharset() {
        assertEquals("text/css" to "utf-8", PinnedClient.contentType("text/css; charset=utf-8"))
        assertEquals("application/json" to "UTF-8", PinnedClient.contentType("application/json;charset=UTF-8"))
        assertEquals("image/jpeg" to null, PinnedClient.contentType("image/jpeg"))
        assertEquals("text/html" to "utf-8", PinnedClient.contentType("text/html; charset=\"utf-8\""))
        assertEquals("application/octet-stream" to null, PinnedClient.contentType(null))
        assertEquals("application/octet-stream" to null, PinnedClient.contentType(""))
    }
}
