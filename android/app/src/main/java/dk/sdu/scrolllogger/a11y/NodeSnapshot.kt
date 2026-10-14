package dk.sdu.scrolllogger.a11y

/**
 * OS-agnostic view of an accessibility node for unit tests.
 * Android AccessibilityNodeInfo is mapped into this; fixtures are JSON of the same shape.
 */
data class NodeSnapshot(
    val text: String? = null,
    val contentDescription: String? = null,
    val viewId: String? = null,
    val className: String? = null,
    val clickable: Boolean = false,
    val selected: Boolean = false,
    val children: List<NodeSnapshot> = emptyList(),
) {
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
}
