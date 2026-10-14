package dk.sdu.scrolllogger

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import dk.sdu.scrolllogger.queue.EventQueue
import dk.sdu.scrolllogger.sync.Prefs

class ScrollLoggerApp : Application() {
    lateinit var eventQueue: EventQueue
        private set
    lateinit var prefs: Prefs
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        prefs = Prefs(this)
        eventQueue = EventQueue(filesDir.resolve("queue"))
        createNotificationChannel()
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            NOTIFICATION_CHANNEL_ID,
            getString(R.string.notification_channel_name),
            NotificationManager.IMPORTANCE_LOW,
        )
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(channel)
    }

    companion object {
        const val NOTIFICATION_CHANNEL_ID = "scroll_logging"
        const val NOTIFICATION_ID = 42
        lateinit var instance: ScrollLoggerApp
            private set
    }
}
