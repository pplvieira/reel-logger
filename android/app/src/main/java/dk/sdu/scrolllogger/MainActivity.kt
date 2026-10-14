package dk.sdu.scrolllogger

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import dk.sdu.scrolllogger.databinding.ActivityMainBinding
import dk.sdu.scrolllogger.sync.SyncWorker

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val prefs = ScrollLoggerApp.instance.prefs
        binding.loggingSwitch.isChecked = prefs.loggingEnabled
        binding.debugA11ySwitch.isChecked = prefs.debugRawA11y
        binding.baseUrlInput.setText(prefs.baseUrl)
        binding.userIdInput.setText(prefs.userId)
        binding.deviceIdInput.setText(prefs.deviceId)
        binding.apiTokenInput.setText(prefs.apiToken)

        binding.loggingSwitch.setOnCheckedChangeListener { _, checked ->
            prefs.loggingEnabled = checked
            if (checked) {
                maybeRequestNotificationPermission()
                startForegroundLogging()
            } else {
                stopService(Intent(this, LoggingForegroundService::class.java))
            }
            refreshStatus()
        }
        binding.debugA11ySwitch.setOnCheckedChangeListener { _, checked ->
            prefs.debugRawA11y = checked
        }
        binding.openAccessibilityButton.setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
        binding.exportButton.setOnClickListener { shareQueue() }
        binding.syncButton.setOnClickListener {
            SyncWorker.enqueue(this)
            Toast.makeText(this, "Sync enqueued", Toast.LENGTH_SHORT).show()
        }
        binding.clearExportedButton.setOnClickListener {
            ScrollLoggerApp.instance.eventQueue.clearAcknowledged()
            refreshStatus()
            Toast.makeText(this, "Cleared acknowledged lines", Toast.LENGTH_SHORT).show()
        }
        binding.saveConfigButton.setOnClickListener {
            prefs.baseUrl = binding.baseUrlInput.text?.toString().orEmpty()
            prefs.userId = binding.userIdInput.text?.toString().orEmpty()
            prefs.deviceId = binding.deviceIdInput.text?.toString().orEmpty()
            prefs.apiToken = binding.apiTokenInput.text?.toString().orEmpty()
            Toast.makeText(this, "Saved", Toast.LENGTH_SHORT).show()
            refreshStatus()
        }
    }

    override fun onResume() {
        super.onResume()
        refreshStatus()
        if (ScrollLoggerApp.instance.prefs.loggingEnabled) {
            startForegroundLogging()
        }
    }

    private fun refreshStatus() {
        val prefs = ScrollLoggerApp.instance.prefs
        val a11y = isAccessibilityEnabled()
        val lines = ScrollLoggerApp.instance.eventQueue.lineCount()
        val path = ScrollLoggerApp.instance.eventQueue.path().absolutePath
        binding.statusText.text = buildString {
            appendLine("Accessibility: ${if (a11y) "ENABLED" else "OFF — open settings"}")
            appendLine("Target package: com.instagram.android")
            appendLine("Logging: ${if (prefs.loggingEnabled) "ON" else "off"}")
            appendLine("Queue lines: $lines")
            appendLine("Queue path: $path")
            appendLine("Sync URL: ${prefs.baseUrl.ifBlank { "(not set)" }}")
            appendLine("user_id: ${prefs.userId.ifBlank { "(not set)" }}")
            appendLine("device_id: ${prefs.deviceId.ifBlank { "(not set)" }}")
            appendLine("Logger: ${BuildConfig.LOGGER_VERSION}")
        }
    }

    private fun isAccessibilityEnabled(): Boolean {
        val enabled = Settings.Secure.getString(
            contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES,
        ) ?: return false
        val expected = "$packageName/${packageName}.a11y.ScrollAccessibilityService"
        return enabled.split(':').any { it.equals(expected, ignoreCase = true) }
    }

    private fun startForegroundLogging() {
        ContextCompat.startForegroundService(
            this,
            Intent(this, LoggingForegroundService::class.java),
        )
    }

    private fun shareQueue() {
        val file = ScrollLoggerApp.instance.eventQueue.path()
        ScrollLoggerApp.instance.eventQueue.markExported()
        val uri = FileProvider.getUriForFile(this, "$packageName.fileprovider", file)
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        startActivity(Intent.createChooser(intent, "Share queue"))
    }

    private fun maybeRequestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    1001,
                )
            }
        }
    }
}
