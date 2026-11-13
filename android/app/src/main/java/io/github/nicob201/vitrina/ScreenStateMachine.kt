package io.github.nicob201.vitrina

/** What the screen should do after one poll of the Mac. */
data class ScreenActions(val keepScreenOn: Boolean, val wake: Boolean, val reload: Boolean)

/**
 * Follows the Mac: keep the screen on while it answers, let it go after [failuresToRelease] misses in a row
 * (about a minute at one poll every 20 s), and wake it only when the Mac comes back after being away.
 * The power button is not an input: if the user turns the screen off while the Mac answers, nothing turns it on.
 */
class ScreenStateMachine(private val failuresToRelease: Int = 3) {
    private var failures = failuresToRelease // starts as "Mac away"

    fun onPoll(ok: Boolean): ScreenActions {
        if (ok) {
            val cameBack = failures >= failuresToRelease
            failures = 0
            return ScreenActions(keepScreenOn = true, wake = cameBack, reload = cameBack)
        }
        if (failures < failuresToRelease) failures++
        return ScreenActions(keepScreenOn = failures < failuresToRelease, wake = false, reload = false)
    }
}
