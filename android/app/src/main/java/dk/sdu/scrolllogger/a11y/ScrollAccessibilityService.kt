package dk.sdu.scrolllogger.a11y

import android.accessibilityservice.AccessibilityService
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.view.accessibility.AccessibilityEvent
import dk.sdu.scrolllogger.ScrollLoggerApp

class ScrollAccessibilityService : AccessibilityService() {
    private val reelDetector = ReelDetector()
    private val interactionDetector = InteractionDetector()
    private var lastPackage: String? = null
    private var lastProcessMs = 0L

    private val screenReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == Intent.ACTION_SCREEN_OFF) {
                emitAll(reelDetector.onScreenOff())
            }
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        registerReceiver(screenReceiver, IntentFilter(Intent.ACTION_SCREEN_OFF))
    }

    override fun onDestroy() {
        try {
            unregisterReceiver(screenReceiver)
        } catch (_: Exception) {
        }
        super.onDestroy()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return
        val app = ScrollLoggerApp.instance
        if (!app.prefs.loggingEnabled) return

        val pkg = event.packageName?.toString()
        if (pkg != null && pkg != INSTAGRAM_PACKAGE) {
            if (lastPackage == INSTAGRAM_PACKAGE) {
                emitAll(reelDetector.onPackageLost())
            }
            lastPackage = pkg
            return
        }
        if (pkg == INSTAGRAM_PACKAGE) {
            lastPackage = pkg
        }

        val now = System.currentTimeMillis()
        // Throttle content-changed spam while video plays
        if (event.eventType == AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED) {
            if (now - lastProcessMs < 350) return
        }
        lastProcessMs = now

        val eventKind = when (event.eventType) {
            AccessibilityEvent.TYPE_VIEW_SCROLLED -> "scroll"
            AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> "window"
            AccessibilityEvent.TYPE_VIEW_CLICKED -> "click"
            else -> "content"
        }

        if (event.eventType == AccessibilityEvent.TYPE_VIEW_CLICKED) {
            val src = event.source
            try {
                val snap = NodeMapper.from(src, maxDepth = 2)
                if (snap != null) {
                    interactionDetector.onClick(snap, now)?.let { emit(it) }
                }
            } finally {
                src?.recycle()
            }
        }

        val root = rootInActiveWindow ?: return
        try {
            val tree = NodeMapper.from(root) ?: return
            if (app.prefs.debugRawA11y && eventKind != "content") {
                emit(
                    SemanticEvent(
                        type = "raw_a11y",
                        payload = NodeMapper.debugSummary(tree),
                        observedAtMs = now,
                    ),
                )
            }
            emitAll(reelDetector.onTree(tree, eventKind, now))
        } finally {
            root.recycle()
        }
    }

    override fun onInterrupt() {
        emitAll(reelDetector.onPackageLost())
    }

    private fun emitAll(events: List<SemanticEvent>) {
        events.forEach(::emit)
    }

    private fun emit(event: SemanticEvent) {
        ScrollLoggerApp.instance.eventQueue.append(
            type = event.type,
            payload = event.payload,
            observedAtMs = event.observedAtMs,
        )
    }

    companion object {
        const val INSTAGRAM_PACKAGE = "com.instagram.android"
    }
}
