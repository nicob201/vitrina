package io.github.nicob201.vitrina

/**
 * From the poll service to the kiosk, in the same process, on the main thread. MainActivity listens while
 * resumed. [origin] is the address that answered (cable first), null if none; [repair] means the Mac refused
 * our key (another phone was paired or the key was deleted).
 */
object ScreenBus {
    @Volatile var listener: ((actions: ScreenActions, origin: String?, repair: Boolean) -> Unit)? = null
    @Volatile var last: ScreenActions? = null
}
