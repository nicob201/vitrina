package io.github.nicob201.vitrina

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.Typeface
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView

/**
 * Takes the pairing from `python3 server.py pair`. Only adb's shell can open it: the manifest guards it
 * with android.permission.DUMP, which no regular app can hold.
 */
class PairActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val info = Pairing.parse(
            intent.getStringExtra("key"),
            intent.getStringExtra("fingerprint"),
            intent.getIntExtra("port", -1),
            intent.getStringExtra("wifi_ip"),
        )
        if (info == null) {
            setContentView(messageView(this, getString(R.string.pairing_invalid))) // what was saved stays as it was
            return
        }
        SecureStore(this).save(info)
        setContentView(messageView(this, getString(R.string.paired)))
        handler.postDelayed({
            startActivity(Intent(this, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK))
            finish()
        }, 3000)
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }
}

/** A centered message in the page's colors, for the app's own screens. */
fun messageView(context: Context, title: String, detail: String? = null): View =
    LinearLayout(context).apply {
        orientation = LinearLayout.VERTICAL
        gravity = Gravity.CENTER
        setBackgroundColor(context.getColor(R.color.night))
        val pad = (32 * resources.displayMetrics.density).toInt()
        setPadding(pad, pad, pad, pad)
        addView(TextView(context).apply {
            text = title
            textSize = 34f
            typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
            setTextColor(context.getColor(R.color.moon))
            gravity = Gravity.CENTER
        })
        if (detail != null) addView(TextView(context).apply {
            text = detail
            textSize = 20f
            setTextColor(context.getColor(R.color.mist))
            gravity = Gravity.CENTER
            setPadding(0, pad / 2, 0, 0)
        })
    }
