package io.github.nicob201.vitrina

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONObject
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** The pairing, encrypted with an AES-256-GCM key that never leaves the Android Keystore. */
class SecureStore(context: Context) {
    private val prefs = context.getSharedPreferences("pairing", Context.MODE_PRIVATE)

    fun save(info: PairingInfo) {
        val json = JSONObject()
            .put("key", info.key).put("fingerprint", info.fingerprint)
            .put("port", info.port).put("wifiIp", info.wifiIp)
            .toString()
        val cipher = Cipher.getInstance(TRANSFORMATION).apply { init(Cipher.ENCRYPT_MODE, secretKey()) }
        val data = cipher.doFinal(json.toByteArray(Charsets.UTF_8))
        prefs.edit()
            .putString("iv", Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .putString("data", Base64.encodeToString(data, Base64.NO_WRAP))
            .commit() // synchronous: the Mac only keeps its new key once this screen is up
    }

    /** Null on any trouble (nothing saved, corrupt data, Keystore key gone): the app then asks to pair again. */
    fun load(): PairingInfo? = try {
        val iv = Base64.decode(prefs.getString("iv", null), Base64.NO_WRAP)
        val data = Base64.decode(prefs.getString("data", null), Base64.NO_WRAP)
        val cipher = Cipher.getInstance(TRANSFORMATION).apply {
            init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(128, iv))
        }
        val o = JSONObject(String(cipher.doFinal(data), Charsets.UTF_8))
        Pairing.parse(o.getString("key"), o.getString("fingerprint"), o.getInt("port"), o.getString("wifiIp"))
    } catch (e: Exception) {
        null
    }

    fun clear() {
        prefs.edit().clear().commit()
    }

    private fun secretKey(): SecretKey {
        val ks = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (ks.getKey(ALIAS, null) as? SecretKey)?.let { return it }
        val gen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE)
        gen.init(
            KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build()
        )
        return gen.generateKey()
    }

    private companion object {
        const val KEYSTORE = "AndroidKeyStore"
        const val ALIAS = "vitrina-pairing"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
    }
}
