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

    @Test
    fun interactionDebouncesDuplicateClicks() {
        val detector = InteractionDetector(debounceMs = 600)
        val node = NodeSnapshot(contentDescription = "Share", clickable = true)
        assertThat(detector.onClick(node, 1_000)).isNotNull()
        assertThat(detector.onClick(node, 1_200)).isNull()
        assertThat(detector.onClick(node, 2_000)).isNotNull()
    }

    @Test
    fun extractCaptionIgnoresSendPostChrome() {
        val caption = ReelDetector.extractCaption(
            listOf(
                "Reels",
                "travel_notes",
                "Send post. Button. Double-tap to choose who to send this post to.",
                "Real caption about the harbour",
            ),
            "travel_notes",
        )
        assertThat(caption).isEqualTo("Real caption about the harbour")
    }

    @Test
    fun extractCreatorRejectsEngagementCounts() {
        val handle = ReelDetector.extractCreator(
            listOf("Reels", "15.6K", "70.8K", "good_creator", "Some caption text here"),
        )
        assertThat(handle).isEqualTo("good_creator")
    }

    @Test
    fun shareOverlayDoesNotEndSession() {
        val detector = ReelDetector(minReelIntervalMs = 0)
        detector.onTree(FixtureLoader.load("reels_surface.json"), "window", 1_000)
        val overlay = NodeSnapshot(
            children = listOf(
                NodeSnapshot(text = "Send to"),
                NodeSnapshot(contentDescription = "Send post. Button. Double-tap to choose who to send this post to."),
                NodeSnapshot(text = "Search"),
            ),
        )
        val events = detector.onTree(overlay, "window", 2_000)
        assertThat(events).isEmpty()
        // Still open: next reels tree should not emit session_start again
        val back = detector.onTree(FixtureLoader.load("reels_surface.json"), "window", 3_000)
        assertThat(back.map { it.type }).doesNotContain("session_start")
    }

    @Test
    fun chromeCaptionChurnDoesNotOpenNewReel() {
        val detector = ReelDetector(minReelIntervalMs = 0)
        detector.onTree(FixtureLoader.load("reels_surface.json"), "window", 1_000)
        val chromeTree = NodeSnapshot(
            children = listOf(
                NodeSnapshot(text = "Reels"),
                NodeSnapshot(text = "For you"),
                NodeSnapshot(text = "travel_notes"),
                NodeSnapshot(
                    contentDescription = "Send post. Button. Double-tap to choose who to send this post to.",
                ),
                NodeSnapshot(contentDescription = "Like button", clickable = true),
                NodeSnapshot(contentDescription = "Comment", clickable = true),
                NodeSnapshot(contentDescription = "Share", clickable = true),
            ),
        )
        val events = detector.onTree(chromeTree, "content", 2_000)
        assertThat(events.map { it.type }).doesNotContain("reel_shown")
    }
}
