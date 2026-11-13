package io.github.nicob201.vitrina

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ScreenStateMachineTest {
    private val m = ScreenStateMachine()
    private val keepOn = ScreenActions(keepScreenOn = true, wake = false, reload = false)
    private val release = ScreenActions(keepScreenOn = false, wake = false, reload = false)
    private val wakeUp = ScreenActions(keepScreenOn = true, wake = true, reload = true)

    @Test fun firstSuccessWakesAndReloads() = assertEquals(wakeUp, m.onPoll(true))

    @Test fun failuresBeforeTheMacEverAnswersDoNothing() {
        repeat(5) { assertEquals(release, m.onPoll(false)) }
    }

    @Test fun laterSuccessesOnlyKeepOn() {
        m.onPoll(true)
        assertEquals(keepOn, m.onPoll(true))
    }

    @Test fun twoFailuresStillKeepOn() {
        m.onPoll(true)
        m.onPoll(false)
        assertTrue(m.onPoll(false).keepScreenOn)
    }

    @Test fun thirdFailureReleases() {
        m.onPoll(true)
        repeat(2) { m.onPoll(false) }
        assertEquals(release, m.onPoll(false))
        assertEquals(release, m.onPoll(false)) // and stays released
    }

    @Test fun comingBackAfterReleaseWakesOnce() {
        m.onPoll(true)
        repeat(3) { m.onPoll(false) }
        assertEquals(wakeUp, m.onPoll(true))
        assertEquals(keepOn, m.onPoll(true))
    }

    @Test fun aBlipDoesNotWake() {
        m.onPoll(true)
        m.onPoll(false)
        m.onPoll(false)
        assertEquals(keepOn, m.onPoll(true))
    }

    @Test fun failuresAreCountedFromScratchAfterABlip() {
        m.onPoll(true)
        repeat(2) { m.onPoll(false) }
        m.onPoll(true)
        repeat(2) { m.onPoll(false) }
        assertTrue(m.onPoll(false).let { !it.keepScreenOn })
    }

    @Test fun customThreshold() {
        val one = ScreenStateMachine(failuresToRelease = 1)
        one.onPoll(true)
        assertEquals(release, one.onPoll(false))
        assertEquals(wakeUp, one.onPoll(true))
    }
}
