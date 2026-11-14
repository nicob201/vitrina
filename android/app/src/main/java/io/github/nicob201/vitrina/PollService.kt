package io.github.nicob201.vitrina

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import kotlin.concurrent.thread

/** Asks the Mac every 20 s whether vitrina is running there, and turns the screen on when it comes back. */
class PollService : Service() {
    private val main = Handler(Looper.getMainLooper())
    @Volatile private var running = false
    private var worker: Thread? = null
    private var cpu: PowerManager.WakeLock? = null
    private var connected: Boolean? = null
    private val notifications by lazy { getSystemService(NotificationManager::class.java) }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (running) return START_STICKY
        running = true
        notifications.createNotificationChannel(
            NotificationChannel(STATUS_CHANNEL, getString(R.string.channel_status), NotificationManager.IMPORTANCE_LOW))
        notifications.createNotificationChannel(
            NotificationChannel(WAKE_CHANNEL, getString(R.string.channel_wake), NotificationManager.IMPORTANCE_HIGH))
        val status = statusNotification(false)
        if (Build.VERSION.SDK_INT >= 34) startForeground(STATUS_ID, status, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        else startForeground(STATUS_ID, status)
        // Without it the CPU sleeps with the screen off and the polling stops. The phone lives on a charger.
        cpu = getSystemService(PowerManager::class.java)
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "vitrina:poll").apply { setReferenceCounted(false); acquire() }
        worker = thread(name = "vitrina-poll") { loop() }
        return START_STICKY
    }

    override fun onDestroy() {
        running = false
        worker?.interrupt()
        cpu?.release()
        super.onDestroy()
    }

    private fun loop() {
        val machine = ScreenStateMachine()
        while (running) {
            val info = SecureStore(this).load()
            if (info == null) {
                main.post { stopSelf() }
                return
            }
            var origin: String? = null
            var repair = false
            for (o in Pairing.origins(info)) {
                when (PinnedClient.get(o, "/api/state", info)) {
                    200 -> { origin = o; break }
                    401 -> repair = true
                }
            }
            val actions = machine.onPoll(origin != null)
            // Wake only when vitrina isn't already in front (it listens while resumed). The page then
            // reloads from the wake intent; otherwise from the listener: once either way.
            val woke = actions.wake && ScreenBus.listener == null
            if (woke) wake()
            showStatus(origin != null)
            val delivered = actions.copy(reload = actions.reload && !woke)
            main.post {
                ScreenBus.last = delivered
                ScreenBus.listener?.invoke(delivered, origin, repair)
            }
            try {
                Thread.sleep(POLL_MS)
            } catch (e: InterruptedException) {
                return
            }
        }
    }

    /**
     * Found on the Nokia (Android 12): a full-screen notification is the only way that turns the screen on AND
     * brings vitrina up when another app was in front; a plain startActivity from here is blocked then.
     */
    private fun wake() {
        val open = Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK).putExtra(EXTRA_RELOAD, true)
        val pending = PendingIntent.getActivity(this, 0, open, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        notifications.notify(WAKE_ID, Notification.Builder(this, WAKE_CHANNEL)
            .setSmallIcon(R.drawable.ic_notify)
            .setContentTitle(getString(R.string.mac_back))
            .setCategory(Notification.CATEGORY_ALARM)
            .setFullScreenIntent(pending, true)
            .setAutoCancel(true)
            .build())
        try {
            startActivity(open) // enough when vitrina is already the app in front
        } catch (e: RuntimeException) {
            // blocked from the background; the notification above takes care of it
        }
    }

    private fun showStatus(now: Boolean) {
        if (now == connected) return
        connected = now
        notifications.notify(STATUS_ID, statusNotification(now))
    }

    private fun statusNotification(connected: Boolean): Notification {
        val open = PendingIntent.getActivity(this, 1, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        return Notification.Builder(this, STATUS_CHANNEL)
            .setSmallIcon(R.drawable.ic_notify)
            .setContentTitle(getString(if (connected) R.string.notif_connected else R.string.notif_waiting))
            .setContentIntent(open)
            .setOngoing(true)
            .build()
    }

    companion object {
        const val WAKE_ID = 2
        const val EXTRA_RELOAD = "reload"
        private const val STATUS_ID = 1
        private const val STATUS_CHANNEL = "status"
        private const val WAKE_CHANNEL = "wake"
        private const val POLL_MS = 20_000L
    }
}
