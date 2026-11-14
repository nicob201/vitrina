package io.github.nicob201.vitrina

import android.annotation.SuppressLint
import android.app.Activity
import android.app.KeyguardManager
import android.app.NotificationManager
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.LocaleList
import android.os.Looper
import android.view.MotionEvent
import android.view.View
import android.view.ViewConfiguration
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.WindowManager
import android.webkit.CookieManager
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import java.io.ByteArrayInputStream
import java.io.IOException
import kotlin.concurrent.thread
import kotlin.math.hypot

/** The kiosk: vitrina's page, full screen, from the paired Mac only. Also the phone's home screen. */
class MainActivity : Activity() {
    private lateinit var web: WebView
    private val main = Handler(Looper.getMainLooper())
    @Volatile private var info: PairingInfo? = null // the pairing the page is shown with (read by the web view's threads)
    private var loadedOrigin: String? = null // where the page came from; null while a message is shown
    private val retry = Runnable { connect() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // When the Mac comes back the poll service brings this up: show it over the lock screen, screen on.
        if (Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON)
        }
        web = buildWebView()
        // The key never goes into a cookie (every request carries it as a header, see PinnedWebClient);
        // also wipe any cookie an older version of the app left on disk.
        CookieManager.getInstance().apply {
            setAcceptCookie(false)
            removeAllCookies(null)
            flush()
        }
        if (Build.VERSION.SDK_INT >= 33) {
            onBackInvokedDispatcher.registerOnBackInvokedCallback(0) {} // a kiosk has nowhere to go back to
        }
    }

    override fun onResume() {
        super.onResume()
        hideSystemBars()
        getSystemService(NotificationManager::class.java).cancel(PollService.WAKE_ID)
        refresh()
    }

    private fun refresh() {
        val current = SecureStore(this).load()
        if (current == null) {
            info = null
            showMessage(R.string.unpaired_title, R.string.pair_how)
            return
        }
        startForegroundService(Intent(this, PollService::class.java))
        ScreenBus.listener = ::onPoll
        ScreenBus.last?.let { keepScreenOn(it.keepScreenOn) }
        if (Guide.pending(this)) {
            info = null // connect once the guide is done
            main.removeCallbacks(retry)
            showView(Guide.view(this) { refresh() })
        } else if (current != info) {
            info = current // first start, new pairing, or a new WiFi address from the settings
            connect()
        }
    }

    override fun onPause() {
        ScreenBus.listener = null
        super.onPause()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        getSystemService(NotificationManager::class.java).cancel(PollService.WAKE_ID)
        if (intent.getBooleanExtra(PollService.EXTRA_RELOAD, false) && info != null) connect() // the Mac is back
    }

    private fun onPoll(actions: ScreenActions, origin: String?, repair: Boolean) {
        keepScreenOn(actions.keepScreenOn)
        if (info == null) return
        // Reload when the Mac comes back, when the key was refused, or when the page should come from the
        // other address (cable plugged in or pulled out).
        if (actions.reload || (repair && loadedOrigin != null) || (origin != null && origin != loadedOrigin)) connect()
    }

    private fun keepScreenOn(on: Boolean) {
        if (on) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) hideSystemBars()
    }

    @Deprecated("Back does nothing in the kiosk")
    @Suppress("DEPRECATION")
    override fun onBackPressed() {
    }

    override fun onDestroy() {
        main.removeCallbacksAndMessages(null)
        web.destroy()
        super.onDestroy()
    }

    /** Ask each origin (cable first) whether the Mac answers with our key, then show the page or say why not. */
    private fun connect() {
        main.removeCallbacks(retry)
        val pairing = info ?: return
        thread {
            val codes = Pairing.origins(pairing).map { it to PinnedClient.get(it, "/api/state", pairing) }
            main.post {
                if (pairing != info) return@post // the pairing changed meanwhile
                val answering = codes.firstOrNull { it.second == 200 }?.first
                when {
                    answering != null -> load(answering)
                    codes.any { it.second == 401 } -> showProblem(R.string.repair_title, R.string.repair_how)
                    codes.any { it.second == PinnedClient.WRONG_CERT } ->
                        showProblem(R.string.not_your_mac_title, R.string.not_your_mac_detail)
                    else -> showProblem(R.string.waiting_title, R.string.waiting_detail)
                }
            }
        }
    }

    private fun load(origin: String) {
        loadedOrigin = origin
        setContentView(web)
        web.loadUrl("$origin/")
    }

    /** Say what's wrong and keep trying: the Mac may start, or the right one come back. Nothing is sent before
     *  the certificate checks out, so retrying is safe. */
    private fun showProblem(title: Int, detail: Int) {
        showMessage(title, detail)
        main.removeCallbacks(retry)
        main.postDelayed(retry, 20_000)
    }

    private fun showMessage(title: Int, detail: Int) = showView(messageView(this, getString(title), getString(detail)))

    private fun showView(view: View) {
        loadedOrigin = null
        web.loadUrl("about:blank") // stop the hidden page from polling
        setContentView(view)
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun buildWebView() = WebView(this).apply {
        settings.apply {
            javaScriptEnabled = true // the page is a script; it gets no bridge to the app
            allowFileAccess = false
            allowContentAccess = false
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            setGeolocationEnabled(false)
        }
        setBackgroundColor(getColor(R.color.night))
        isLongClickable = false
        isHapticFeedbackEnabled = false
        setOnLongClickListener { true } // no text selection or context menu
        webViewClient = PinnedWebClient()
    }

    /**
     * The web view never goes to the network itself: every request the page makes (the page, its data, the
     * photos, the fonts) is made here, through PinnedClient — the Mac's certificate checked by fingerprint, the
     * key as a header. So the key is never handed to the web view, and it never trusts any certificate itself
     * (its own TLS errors keep the default: cancel).
     */
    private inner class PinnedWebClient : WebViewClient() {
        override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse {
            val pairing = info
            val url = request.url.toString()
            if (pairing == null || request.method != "GET" || !Pairing.isPaired(url, pairing)) return empty(403)
            return try {
                val language = request.requestHeaders["Accept-Language"] ?: LocaleList.getDefault().toLanguageTags()
                val conn = PinnedClient.open(url, pairing, mapOf("Accept-Language" to language), readTimeoutMs = 15_000)
                val code = conn.responseCode
                if (code !in 200..299 && code !in 400..599) { // 1xx/3xx: never sent by vitrina, not passed on
                    conn.disconnect()
                    return empty(502)
                }
                if (code == 401 && request.isForMainFrame) main.post { showProblem(R.string.repair_title, R.string.repair_how) }
                val (mime, charset) = PinnedClient.contentType(conn.contentType)
                val body = (if (code >= 400) conn.errorStream else conn.inputStream)
                    ?: ByteArrayInputStream(ByteArray(0)).also { conn.disconnect() }
                val headers = conn.headerFields
                    .filterKeys { it != null && it.lowercase() !in HOP_HEADERS }
                    .mapValues { it.value.joinToString(", ") }
                WebResourceResponse(mime, charset, code, conn.responseMessage?.ifEmpty { null } ?: "OK", headers, body)
            } catch (e: IOException) {
                // The page's own requests turn this into "offline"; a failed page load waits and tries again.
                if (request.isForMainFrame) main.post { showProblem(R.string.waiting_title, R.string.waiting_detail) }
                empty(503)
            }
        }

        override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest) =
            info?.let { Pairing.isPaired(request.url.toString(), it) } != true // nothing outside the paired Mac

        override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
            if (request.isForMainFrame) showProblem(R.string.waiting_title, R.string.waiting_detail) // went away mid-load
        }
    }

    // Holding a finger still for 3 s opens the settings; taps still reach the page (tap = next panel).
    private val openSettings = Runnable {
        longPress = true
        val now = android.os.SystemClock.uptimeMillis()
        val cancel = MotionEvent.obtain(now, now, MotionEvent.ACTION_CANCEL, 0f, 0f, 0)
        window.superDispatchTouchEvent(cancel) // the page must not see this press as a tap
        cancel.recycle()
        // The page shows over the lock screen; the settings don't: unlock first (PIN, if the phone has one).
        val keyguard = getSystemService(KeyguardManager::class.java)
        val settings = Intent(this, SettingsActivity::class.java)
        if (!keyguard.isKeyguardLocked) startActivity(settings)
        else keyguard.requestDismissKeyguard(this, object : KeyguardManager.KeyguardDismissCallback() {
            override fun onDismissSucceeded() = startActivity(settings)
        })
    }
    private var longPress = false
    private var downX = 0f
    private var downY = 0f

    override fun dispatchTouchEvent(ev: MotionEvent): Boolean {
        when (ev.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                longPress = false
                downX = ev.x
                downY = ev.y
                main.postDelayed(openSettings, 3000)
            }
            MotionEvent.ACTION_MOVE ->
                if (hypot(ev.x - downX, ev.y - downY) > ViewConfiguration.get(this).scaledTouchSlop) main.removeCallbacks(openSettings)
            MotionEvent.ACTION_POINTER_DOWN, MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> main.removeCallbacks(openSettings)
        }
        return if (longPress) true else super.dispatchTouchEvent(ev)
    }

    private fun hideSystemBars() {
        if (Build.VERSION.SDK_INT >= 30) {
            window.insetsController?.apply {
                hide(WindowInsets.Type.systemBars())
                systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            }
        } else {
            @Suppress("DEPRECATION")
            window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or
                View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
                View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
        }
    }
}

private val HOP_HEADERS = setOf("content-type", "content-length", "content-encoding", "transfer-encoding", "connection")

private fun empty(code: Int) =
    WebResourceResponse("text/plain", "utf-8", code, "vitrina", emptyMap(), ByteArrayInputStream(ByteArray(0)))
