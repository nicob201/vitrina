package io.github.nicob201.vitrina

import android.Manifest
import android.app.Activity
import android.app.NotificationManager
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/** First start: the phone settings vitrina needs to follow the Mac. Shown until all are set or "Done" is tapped. */
object Guide {
    private class Step(val label: Int, val done: Boolean, val fix: (Activity) -> Unit)

    private fun steps(a: Activity): List<Step> {
        val steps = mutableListOf(
            Step(R.string.guide_home, isDefaultHome(a)) { open(it, Settings.ACTION_HOME_SETTINGS) },
            Step(R.string.guide_timeout, Settings.System.getInt(a.contentResolver, Settings.System.SCREEN_OFF_TIMEOUT, 0) in 1..60_000) {
                open(it, Settings.ACTION_DISPLAY_SETTINGS)
            },
            // With it on, the screen never turns off while charging, so it can't follow the Mac.
            Step(R.string.guide_stay_awake, Settings.Global.getInt(a.contentResolver, Settings.Global.STAY_ON_WHILE_PLUGGED_IN, 0) == 0) {
                open(it, Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS)
            },
        )
        if (Build.VERSION.SDK_INT >= 33) {
            steps += Step(R.string.guide_notifications,
                a.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) {
                it.requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
            }
        }
        if (Build.VERSION.SDK_INT >= 34) {
            steps += Step(R.string.guide_full_screen, a.getSystemService(NotificationManager::class.java).canUseFullScreenIntent()) {
                open(it, Settings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT, Uri.parse("package:${it.packageName}"))
            }
        }
        return steps
    }

    fun pending(a: Activity) = !prefs(a).getBoolean("done", false) && steps(a).any { !it.done }

    fun view(a: Activity, onDone: () -> Unit): View {
        val pad = (24 * a.resources.displayMetrics.density).toInt()
        val column = LinearLayout(a).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad * 2, pad, pad * 2, pad)
        }
        column.addView(text(a, a.getString(R.string.guide_title), 30f, R.color.moon, bold = true))
        column.addView(text(a, a.getString(R.string.guide_why), 18f, R.color.mist).apply { setPadding(0, pad / 3, 0, pad / 2) })
        for (step in steps(a)) {
            val row = LinearLayout(a).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                setPadding(0, pad / 4, 0, pad / 4)
            }
            val label = (if (step.done) "✓  " else "•  ") + a.getString(step.label)
            row.addView(text(a, label, 20f, if (step.done) R.color.mist else R.color.moon),
                LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            if (!step.done) row.addView(Button(a).apply {
                text = a.getString(R.string.guide_open)
                setOnClickListener { step.fix(a) }
            })
            column.addView(row)
        }
        column.addView(Button(a).apply {
            text = a.getString(R.string.guide_done)
            setOnClickListener {
                prefs(a).edit().putBoolean("done", true).apply()
                onDone()
            }
        }, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
            topMargin = pad / 2
        })
        return ScrollView(a).apply {
            setBackgroundColor(a.getColor(R.color.night))
            addView(column)
        }
    }

    private fun isDefaultHome(c: Context): Boolean {
        val home = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
        return c.packageManager.resolveActivity(home, PackageManager.MATCH_DEFAULT_ONLY)?.activityInfo?.packageName == c.packageName
    }

    private fun open(a: Activity, action: String, data: Uri? = null) {
        try {
            a.startActivity(Intent(action, data))
        } catch (e: ActivityNotFoundException) {
            a.startActivity(Intent(Settings.ACTION_SETTINGS))
        }
    }

    private fun prefs(c: Context) = c.getSharedPreferences("guide", Context.MODE_PRIVATE)

    private fun text(c: Context, value: String, size: Float, color: Int, bold: Boolean = false) = TextView(c).apply {
        text = value
        textSize = size
        setTextColor(c.getColor(color))
        if (bold) typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
    }
}
