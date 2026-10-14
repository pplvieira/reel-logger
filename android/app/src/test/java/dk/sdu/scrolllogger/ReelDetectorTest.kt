package dk.sdu.scrolllogger

import com.google.common.truth.Truth.assertThat
import dk.sdu.scrolllogger.a11y.InteractionDetector
import dk.sdu.scrolllogger.a11y.NodeSnapshot
import dk.sdu.scrolllogger.a11y.ReelDetector
import org.junit.Test

class ReelDetectorTest {
    @Test
    fun sessionAndReelShownFromReelsSurface() {
        val detector = ReelDetector(minReelIntervalMs = 0)
        val root = FixtureLoader.load("reels_surface.json")
        val events = detector.onTree(root, "window", nowMs = 1_000)
        assertThat(events.map { it.type }).containsExactly("session_start", "reel_shown").inOrder()
        val shown = events.first { it.type == "reel_shown" }
        assertThat(shown.payload["creator_handle"]).isEqualTo("travel_notes")
        assertThat(shown.payload["confidence"]).isEqualTo(0.9)
    }

    @Test
    fun scrollToNextReelEmitsHiddenThenShown() {
        val detector = ReelDetector(minReelIntervalMs = 0)
        detector.onTree(FixtureLoader.load("reels_surface.json"), "window", 1_000)
        val events = detector.onTree(FixtureLoader.load("reel_next.json"), "scroll", 2_000)
        assertThat(events.map { it.type }).containsExactly("reel_hidden", "reel_shown").inOrder()
        assertThat(events.last().payload["creator_handle"]).isEqualTo("other_creator")
    }

    @Test
    fun packageLostEndsSession() {
        val detector = ReelDetector(minReelIntervalMs = 0)
        detector.onTree(FixtureLoader.load("reels_surface.json"), "window", 1_000)
        val events = detector.onPackageLost(2_000)
        assertThat(events.map { it.type }).contains("reel_hidden")
        assertThat(events.map { it.type }).contains("session_end")
        assertThat(events.last().payload["end_reason"]).isEqualTo("leave")
    }

    @Test
    fun likeClickMapsToInteraction() {
        val detector = InteractionDetector()
        val node = NodeSnapshot(contentDescription = "Like button", clickable = true)
        val event = detector.onClick(node, 1_000)
        assertThat(event).isNotNull()
        assertThat(event!!.payload["kind"]).isEqualTo("like")
    }
}
