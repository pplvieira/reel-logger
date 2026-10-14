package dk.sdu.scrolllogger.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import dk.sdu.scrolllogger.ScrollLoggerApp

class SyncWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        val app = ScrollLoggerApp.instance
        val prefs = app.prefs
        if (prefs.baseUrl.isBlank() || prefs.userId.isBlank() || prefs.deviceId.isBlank()) {
            return Result.failure()
        }
        val client = IngestClient(prefs.baseUrl, prefs.apiToken, prefs.userId, prefs.deviceId)
        var total = 0
        while (total < 2000) {
            val batch = app.eventQueue.unreadEvents(100)
            if (batch.isEmpty()) break
            val outcome = client.postEvents(batch)
            if (outcome.isFailure) {
                return if (total > 0) Result.success() else Result.retry()
            }
            app.eventQueue.markSynced(batch.size)
            total += batch.size
            if (batch.size < 100) break
        }
        return Result.success()
    }

    companion object {
        private const val UNIQUE = "scroll_logger_sync"

        fun enqueue(context: Context) {
            val req = OneTimeWorkRequestBuilder<SyncWorker>().build()
            WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE,
                ExistingWorkPolicy.KEEP,
                req,
            )
        }
    }
}
