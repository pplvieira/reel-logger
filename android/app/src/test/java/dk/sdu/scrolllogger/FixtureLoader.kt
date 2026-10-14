package dk.sdu.scrolllogger

import dk.sdu.scrolllogger.a11y.NodeSnapshot
import org.json.JSONObject

object FixtureLoader {
    fun load(name: String): NodeSnapshot {
        val stream = javaClass.classLoader!!.getResourceAsStream("fixtures/$name")
            ?: error("Missing fixture: $name")
        val text = stream.bufferedReader().readText()
        return parse(JSONObject(text))
    }

    fun parse(obj: JSONObject): NodeSnapshot {
        val childrenJson = obj.optJSONArray("children")
        val children = mutableListOf<NodeSnapshot>()
        if (childrenJson != null) {
            for (i in 0 until childrenJson.length()) {
                children.add(parse(childrenJson.getJSONObject(i)))
            }
        }
        return NodeSnapshot(
            text = optionalString(obj, "text"),
            contentDescription = optionalString(obj, "contentDescription"),
            viewId = optionalString(obj, "viewId"),
            className = optionalString(obj, "className"),
            clickable = obj.optBoolean("clickable", false),
            selected = obj.optBoolean("selected", false),
            children = children,
        )
    }

    private fun optionalString(obj: JSONObject, key: String): String? {
        if (!obj.has(key) || obj.isNull(key)) return null
        val value = obj.getString(key)
        return value.takeIf { it.isNotBlank() }
    }
}
