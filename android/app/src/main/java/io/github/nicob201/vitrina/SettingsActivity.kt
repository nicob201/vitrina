package io.github.nicob201.vitrina

import android.app.Activity
import android.content.Intent
import android.graphics.Typeface
import android.os.Bundle
import android.text.InputType
import android.text.method.DigitsKeyListener
import android.view.Gravity
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/** Opened by holding a finger on the screen for 3 s: fix the Mac's WiFi address, or leave vitrina. */
class SettingsActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val store = SecureStore(this)
        val pairing = store.load()
        val pad = (24 * resources.displayMetrics.density).toInt()
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad * 2, pad, pad * 2, pad)
        }
        column.addView(text(getString(R.string.settings_title), 30f, R.color.moon, bold = true))

        if (pairing != null) {
            column.addView(text(getString(R.string.settings_wifi), 18f, R.color.mist).apply { setPadding(0, pad, 0, 0) })
            val status = text("", 16f, R.color.mist)
            val ip = EditText(this).apply {
                setText(pairing.wifiIp)
                hint = getString(R.string.settings_wifi_hint)
                inputType = InputType.TYPE_CLASS_TEXT
                keyListener = DigitsKeyListener.getInstance("0123456789.")
                setTextColor(getColor(R.color.moon))
                setHintTextColor(getColor(R.color.mist))
                textSize = 24f
                setSingleLine()
            }
            column.addView(ip)
            column.addView(button(getString(R.string.settings_save)) {
                val value = ip.text.toString().trim()
                if (value.isEmpty() || Pairing.isIpv4(value)) {
                    store.save(pairing.copy(wifiIp = value))
                    status.text = getString(R.string.settings_saved)
                } else {
                    status.text = getString(R.string.settings_invalid_ip)
                }
            })
            column.addView(status)
        }

        column.addView(button(getString(R.string.settings_exit)) { exitToOtherHome(column, pad) }.apply {
            (layoutParams as? LinearLayout.LayoutParams)?.topMargin = pad
        })
        column.addView(button(getString(R.string.settings_back)) { finish() })
        setContentView(ScrollView(this).apply {
            setBackgroundColor(getColor(R.color.night))
            addView(column)
        })
    }

    @Suppress("DEPRECATION")
    private fun exitToOtherHome(column: LinearLayout, pad: Int) {
        val home = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
        val other = packageManager.queryIntentActivities(home, 0).map { it.activityInfo }
            .firstOrNull { it.packageName != packageName }
        if (other == null) {
            column.addView(text(getString(R.string.settings_no_other_home), 16f, R.color.mist).apply { setPadding(0, pad / 2, 0, 0) })
            return
        }
        startActivity(home.setClassName(other.packageName, other.name).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        finish()
    }

    private fun text(value: String, size: Float, color: Int, bold: Boolean = false) = TextView(this).apply {
        text = value
        textSize = size
        setTextColor(getColor(color))
        if (bold) typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
    }

    private fun button(label: String, onClick: () -> Unit) = Button(this).apply {
        text = label
        gravity = Gravity.CENTER
        setOnClickListener { onClick() }
        layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
    }
}
