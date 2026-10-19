package dk.sdu.scrolllogger.a11y

/**
 * OS-agnostic view of an accessibility node for unit tests and logging.
 * Bounds are screen coordinates when captured on device (null in pure fixtures).
 */
data class NodeSnapshot(
    val text: String? = null,
    val contentDescription: String? = null,
    val viewId: String? = null,
    val className: String? = null,
    val clickable: Boolean = false,
    val selected: Boolean = false,
    val bounds: Bounds? = null,
    val children: List<NodeSnapshot> = emptyList(),
) {
    data class Bounds(
        val left: Int,
        val top: Int,
        val right: Int,
        val bottom: Int,
    ) {
        fun toMap(): Map<String, Int> = mapOf(
            "l" to left,
            "t" to top,
            "r" to right,
            "b" to bottom,
        )
    }

    fun allTexts(): List<String> {
        val out = mutableListOf<String>()
        fun walk(n: NodeSnapshot) {
            n.text?.takeIf { it.isNotBlank() }?.let { out.add(it) }
            n.contentDescription?.takeIf { it.isNotBlank() }?.let { out.add(it) }
            n.children.forEach(::walk)
        }
        walk(this)
        return out
    }

    fun findByDescContains(vararg needles: String): NodeSnapshot? {
        fun walk(n: NodeSnapshot): NodeSnapshot? {
            val hay = listOfNotNull(n.text, n.contentDescription).joinToString(" ").lowercase()
            if (needles.any { hay.contains(it.lowercase()) }) return n
            n.children.forEach { walk(it)?.let { hit -> return hit } }
            return null
        }
        return walk(this)
    }

    /** Flatten nodes that carry text or a description (for raw_a11y export). */
    fun collectLabeledNodes(limit: Int = 80): List<NodeSnapshot> {
        val out = mutableListOf<NodeSnapshot>()
        fun walk(n: NodeSnapshot) {
            if (out.size >= limit) return
            val hasLabel =
                !n.text.isNullOrBlank() || !n.contentDescription.isNullOrBlank()
            if (hasLabel) out.add(n)
            n.children.forEach(::walk)
        }
        walk(this)
        return out
    }
}
