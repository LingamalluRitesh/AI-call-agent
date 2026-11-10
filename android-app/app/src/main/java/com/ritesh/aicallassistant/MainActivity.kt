package com.ritesh.aicallassistant

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.Image
import androidx.compose.ui.res.painterResource
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ritesh.aicallassistant.data.CallFilter
import com.ritesh.aicallassistant.ui.AssistantViewModel
import com.ritesh.aicallassistant.ui.components.CallCard
import com.ritesh.aicallassistant.ui.components.ForwardingDialog
import com.ritesh.aicallassistant.ui.components.ServerSettingsDialog
import com.ritesh.aicallassistant.ui.components.SimulationDialog
import com.ritesh.aicallassistant.ui.components.StatsRow
import com.ritesh.aicallassistant.ui.theme.DarkBackground
import com.ritesh.aicallassistant.ui.theme.DarkSurface
import com.ritesh.aicallassistant.ui.theme.DarkSurfaceVariant
import com.ritesh.aicallassistant.ui.theme.RiteshCallAssistantTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            RiteshCallAssistantTheme {
                AssistantApp()
            }
        }
    }
}

@Composable
fun AssistantApp(viewModel: AssistantViewModel = viewModel()) {
    val uiState by viewModel.uiState.collectAsState()
    val playbackState by viewModel.playbackState.collectAsState()

    var showSimulationDialog by remember { mutableStateOf(false) }
    var showForwardingDialog by remember { mutableStateOf(false) }
    var showSettingsDialog by remember { mutableStateOf(false) }

    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(uiState.snackbarMessage) {
        uiState.snackbarMessage?.let { msg ->
            snackbarHostState.showSnackbar(msg)
            viewModel.clearSnackbar()
        }
    }

    Scaffold(
        containerColor = DarkBackground,
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            AppHeader(
                serverOnline = uiState.serverOnline,
                onOpenSettings = { showSettingsDialog = true }
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Stats Row
            item {
                Spacer(modifier = Modifier.height(4.dp))
                StatsRow(stats = uiState.stats)
            }

            // Quick Actions Bar
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Button(
                        onClick = { showSimulationDialog = true },
                        modifier = Modifier.weight(1.2f),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB))
                    ) {
                        Icon(
                            imageVector = Icons.Default.PlayArrow,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Simulate", fontSize = 13.sp, fontWeight = FontWeight.Bold)
                    }

                    OutlinedButton(
                        onClick = { showForwardingDialog = true },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.outlinedButtonColors(
                            containerColor = DarkSurface,
                            contentColor = Color(0xFFE2E8F0)
                        ),
                        border = androidx.compose.foundation.BorderStroke(1.dp, DarkSurfaceVariant)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Phone,
                            contentDescription = null,
                            tint = Color(0xFF38BDF8),
                            modifier = Modifier.size(14.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("*61*", fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    }

                    IconButton(
                        onClick = { viewModel.refreshAll(isPullRefresh = true) },
                        modifier = Modifier
                            .clip(RoundedCornerShape(12.dp))
                            .background(DarkSurface)
                            .border(1.dp, DarkSurfaceVariant, RoundedCornerShape(12.dp))
                    ) {
                        if (uiState.isLoading || uiState.isRefreshing) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(16.dp),
                                strokeWidth = 2.dp,
                                color = Color(0xFF38BDF8)
                            )
                        } else {
                            Icon(
                                imageVector = Icons.Default.Refresh,
                                contentDescription = "Refresh",
                                tint = Color(0xFF38BDF8),
                                modifier = Modifier.size(18.dp)
                            )
                        }
                    }
                }
            }

            // Filter Tabs
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    FilterChip(
                        selected = uiState.currentFilter == CallFilter.ALL,
                        onClick = { viewModel.setFilter(CallFilter.ALL) },
                        label = { Text("All (${uiState.calls.size})", fontSize = 12.sp) },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = Color(0xFF2563EB),
                            selectedLabelColor = Color.White,
                            containerColor = DarkSurface,
                            labelColor = Color(0xFF94A3B8)
                        )
                    )
                    FilterChip(
                        selected = uiState.currentFilter == CallFilter.CALLBACKS,
                        onClick = { viewModel.setFilter(CallFilter.CALLBACKS) },
                        label = { Text("Callbacks (${uiState.stats.unreadMessages})", fontSize = 12.sp) },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = Color(0xFF2563EB),
                            selectedLabelColor = Color.White,
                            containerColor = DarkSurface,
                            labelColor = Color(0xFF94A3B8)
                        )
                    )
                    FilterChip(
                        selected = uiState.currentFilter == CallFilter.RECORDINGS,
                        onClick = { viewModel.setFilter(CallFilter.RECORDINGS) },
                        label = { Text("Recorded (${uiState.stats.recordedCalls})", fontSize = 12.sp) },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = Color(0xFF2563EB),
                            selectedLabelColor = Color.White,
                            containerColor = DarkSurface,
                            labelColor = Color(0xFF94A3B8)
                        )
                    )
                }
            }

            // Calls List or Empty State
            if (uiState.filteredCalls.isEmpty()) {
                item {
                    EmptyCallsPlaceholder(
                        isOnline = uiState.serverOnline == true,
                        onSimulate = { showSimulationDialog = true },
                        onRefresh = { viewModel.refreshAll() }
                    )
                }
            } else {
                items(uiState.filteredCalls, key = { it.id }) { call ->
                    CallCard(
                        call = call,
                        isExpanded = uiState.expandedCallIds.contains(call.id),
                        transcripts = uiState.transcripts[call.id],
                        isLoadingTranscript = uiState.loadingTranscripts.contains(call.id),
                        playbackState = playbackState,
                        onToggleTranscript = { viewModel.toggleTranscript(call.id) },
                        onPlayAudio = { viewModel.playRecording(call) }
                    )
                }
            }

            item {
                Spacer(modifier = Modifier.height(24.dp))
            }
        }
    }

    if (showSimulationDialog) {
        SimulationDialog(
            isSimulating = uiState.isSimulating,
            onDismiss = { showSimulationDialog = false },
            onRunScenario = { scenario ->
                viewModel.runSimulation(scenario)
            }
        )
    }

    if (showForwardingDialog) {
        ForwardingDialog(onDismiss = { showForwardingDialog = false })
    }

    if (showSettingsDialog) {
        ServerSettingsDialog(
            currentUrl = uiState.serverUrl,
            onDismiss = { showSettingsDialog = false },
            onSaveUrl = { newUrl ->
                viewModel.setServerUrl(newUrl)
            }
        )
    }
}

@Composable
private fun AppHeader(
    serverOnline: Boolean?,
    onOpenSettings: () -> Unit
) {
    Surface(
        color = Color(0xFF111827),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFF1F2937))
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .statusBarsPadding()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Image(
                    painter = painterResource(id = R.drawable.app_logo),
                    contentDescription = "Ritesh AI Logo",
                    modifier = Modifier
                        .size(42.dp)
                        .clip(RoundedCornerShape(12.dp))
                )
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(
                        text = "Ritesh AI Assistant",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFF8FAFC)
                    )
                    Text(
                        text = "RMVS Web Services Receptionist",
                        fontSize = 11.sp,
                        color = Color(0xFF94A3B8)
                    )
                }
            }

            Row(verticalAlignment = Alignment.CenterVertically) {
                ConnectionStatusPill(isOnline = serverOnline)
                Spacer(modifier = Modifier.width(6.dp))
                IconButton(onClick = onOpenSettings, modifier = Modifier.size(32.dp)) {
                    Icon(
                        imageVector = Icons.Default.Settings,
                        contentDescription = "Settings",
                        tint = Color(0xFF94A3B8),
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
        }
    }
}

@Composable
private fun ConnectionStatusPill(isOnline: Boolean?) {
    val (dotColor, text, bgColor, border) = when (isOnline) {
        true -> Quad(Color(0xFF22C55E), "ONLINE", Color(0xFF22C55E).copy(alpha = 0.1f), Color(0xFF22C55E).copy(alpha = 0.3f))
        false -> Quad(Color(0xFFEF4444), "OFFLINE", Color(0xFFEF4444).copy(alpha = 0.1f), Color(0xFFEF4444).copy(alpha = 0.3f))
        null -> Quad(Color(0xFFF59E0B), "CONNECTING", Color(0xFFF59E0B).copy(alpha = 0.1f), Color(0xFFF59E0B).copy(alpha = 0.3f))
    }

    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(20.dp))
            .background(bgColor)
            .border(1.dp, border, RoundedCornerShape(20.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(6.dp)
                    .clip(CircleShape)
                    .background(dotColor)
            )
            Spacer(modifier = Modifier.width(5.dp))
            Text(
                text = text,
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                color = dotColor
            )
        }
    }
}

@Composable
private fun EmptyCallsPlaceholder(
    isOnline: Boolean,
    onSimulate: () -> Unit,
    onRefresh: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 36.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "📞",
            fontSize = 42.sp
        )
        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = if (isOnline) "No Call Activity Yet" else "Cannot Connect to Backend Server",
            fontSize = 16.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFFF8FAFC)
        )
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            text = if (isOnline)
                "Calls forwarded to your AI receptionist will appear here with live transcripts, audio recordings, and callbacks."
            else
                "Make sure your FastAPI server is running (`start_backend.bat`) and check your server URL in settings.",
            fontSize = 12.sp,
            color = Color(0xFF94A3B8),
            textAlign = androidx.compose.ui.text.style.TextAlign.Center,
            modifier = Modifier.padding(horizontal = 24.dp)
        )
        Spacer(modifier = Modifier.height(18.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Button(
                onClick = onSimulate,
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB))
            ) {
                Text("Simulate Test Call", fontSize = 12.sp)
            }
            OutlinedButton(
                onClick = onRefresh,
                colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFF38BDF8))
            ) {
                Text("Refresh", fontSize = 12.sp)
            }
        }
    }
}

private data class Quad<A, B, C, D>(val first: A, val second: B, val third: C, val fourth: D)
