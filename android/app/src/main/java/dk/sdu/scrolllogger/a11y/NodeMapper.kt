package dk.sdu.scrolllogger.a11y

import android.graphics.Rect
import android.view.accessibility.AccessibilityNodeInfo

object NodeMapper {
    fun from(node: AccessibilityNodeInfo?, depth: Int = 0, maxDepth: Int = 12): NodeSnapshot? {
        if (node == null || depth > maxDepth) return null
        val children = mutableListOf<NodeSnapshot>()
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            try {
                from(child, depth + 1, maxDepth)?.let { children.add(it) }
            } finally {
                child.recycle()
            }
        }
        val rect = Rect()
        node.getBoundsInScreen(rect)
        val bounds =
            if (rect.isEmpty) {
                null
            } else {
                NodeSnapshot.Bounds(rect.left, rect.top, rect.right, rect.bottom)
            }
        return NodeSnapshot(
            text = node.text?.toString(),
            contentDescription = node.contentDescription?.toString(),
            viewId = node.viewIdResourceName,
            className = node.className?.toString(),
            clickable = node.isClickable,
            selected = node.isSelected,
            bounds = bounds,
            children = children,
        )
    }

    /**
     * Era B+C debug dump: keep `texts_sample` for older PC parsers;
     * add `nodes` with bounds for spatial preprocess (era C).
     */
    fun debugSummary(
        root: NodeSnapshot,
        textLimit: Int = 40,
        nodeLimit: Int = 80,
        screenWidth: Int = 0,
        screenHeight: Int = 0,
    ): Map<String, Any?> {
        val texts = root.allTexts()
        val labeled = root.collectLabeledNodes(nodeLimit)
        val nodes = labeled.map { n ->
            buildMap<String, Any?> {
                if (!n.text.isNullOrBlank()) put("text", n.text)
                if (!n.contentDescription.isNullOrBlank()) {
                    put("contentDescription", n.contentDescription)
                }
                if (!n.viewId.isNullOrBlank()) put("viewId", n.viewId)
                put("clickable", n.clickable)
                n.bounds?.let { put("bounds", it.toMap()) }
            }
        }
        return buildMap {
            put("text_count", texts.size)
            put("texts_sample", texts.take(textLimit))
            put("nodes", nodes)
            if (screenWidth > 0 && screenHeight > 0) {
                put("screen", mapOf("w" to screenWidth, "h" to screenHeight))
            }
        }
    }
}
