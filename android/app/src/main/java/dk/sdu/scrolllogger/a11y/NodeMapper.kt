package dk.sdu.scrolllogger.a11y

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
        return NodeSnapshot(
            text = node.text?.toString(),
            contentDescription = node.contentDescription?.toString(),
            viewId = node.viewIdResourceName,
            className = node.className?.toString(),
            clickable = node.isClickable,
            selected = node.isSelected,
            children = children,
        )
    }

    /** Compact debug dump for optional raw_a11y events (off by default). */
    fun debugSummary(root: NodeSnapshot, limit: Int = 40): Map<String, Any?> {
        val texts = root.allTexts().take(limit)
        return mapOf(
            "text_count" to root.allTexts().size,
            "texts_sample" to texts,
        )
    }
}
