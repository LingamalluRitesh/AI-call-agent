package com.ritesh.aicallassistant.ui.components

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ritesh.aicallassistant.data.SimulationScenario
import com.ritesh.aicallassistant.ui.theme.DarkBackground
import com.ritesh.aicallassistant.ui.theme.DarkSurface
import com.ritesh.aicallassistant.ui.theme.DarkSurfaceVariant

@Composable
fun SimulationDialog(
    isSimulating: Boolean,
    onDismiss: () -> Unit,
    onRunScenario: (SimulationScenario) -> Unit
) {
    val scenarios = remember {
        listOf(
            SimulationScenario(
                title = "🌐 RMVS Website Inquiry (English)",
                subtitle = "Consent GRANTED • Inquires about custom website",
                callerNumber = "+919876543210",
                language = "en",
                utterances = listOf(
                    "Yes, I agree to recording this conversation.",
                    "Hello, I am looking for a website for my retail shop through RMVS Web Services.",
                    "My name is Amit. Can Ritesh call me back this evening with a consultation?"
                )
            ),
            SimulationScenario(
                title = "🎓 B.Tech Project Consultation (Telugu)",
                subtitle = "సమ్మతి ఇవ్వబడింది • AI & Python Project Discussion",
                callerNumber = "+919705162303",
                language = "te",
                utterances = listOf(
                    "సరేనండి, రికార్డింగ్ చేసుకోవచ్చు.",
                    "నమస్తే అండి, కాలేజ్ B.Tech ప్రాజెక్ట్ గైడెన్స్ కోసం రితేష్ గారిని కలవాలనుకుంటున్నాను.",
                    "నా పేరు సురేష్. ఆయన ఎప్పుడు అందుబాటులో ఉంటారో చెప్పగలరా?"
                )
            ),
            SimulationScenario(
                title = "🛍️ E-Commerce Store Inquiry (Hindi)",
                subtitle = "Consent DECLINED • Zero audio stored on disk",
                callerNumber = "+919123456789",
                language = "hi",
                utterances = listOf(
                    "नहीं, मुझे रिकॉर्डिंग नहीं चाहिए।",
                    "नमस्ते, मुझे अपने नए क्लोदिंग ब्रांड के लिए ऑनलाइन ई-कॉमर्स स्टोर बनवाना है।",
                    "मेरा नाम राहुल है, क्या मुझे कोटेशन मिल सकती है?"
                )
            ),
            SimulationScenario(
                title = "🚨 Server Outage Alert (Emergency)",
                subtitle = "EMERGENCY priority • Immediate callback notification",
                callerNumber = "+919999000111",
                language = "en",
                utterances = listOf(
                    "Yes, record this urgent notice.",
                    "Emergency alert: The production PostgreSQL database has high latency and orders are failing.",
                    "Please have Ritesh check Slack immediately!"
                )
            )
        )
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = {
            Text(
                "⚡ Test Call Simulation",
                color = Color(0xFFF8FAFC),
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(
                    "Select a realistic test call scenario to run through the full AI receptionist pipeline:",
                    fontSize = 12.sp,
                    color = Color(0xFF94A3B8)
                )

                scenarios.forEach { scenario ->
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(DarkBackground)
                            .border(1.dp, DarkSurfaceVariant, RoundedCornerShape(12.dp))
                            .clickable(enabled = !isSimulating) {
                                onRunScenario(scenario)
                                onDismiss()
                            }
                            .padding(12.dp)
                    ) {
                        Column {
                            Text(
                                text = scenario.title,
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF38BDF8)
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = scenario.subtitle,
                                fontSize = 11.sp,
                                color = Color(0xFF94A3B8)
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel", color = Color(0xFF64748B))
            }
        }
    )
}

@Composable
fun ForwardingDialog(onDismiss: () -> Unit) {
    val context = LocalContext.current
    var exoPhone by remember { mutableStateOf("08047360000") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = {
            Text(
                "📞 Vi Call Forwarding Setup",
                color = Color(0xFFF8FAFC),
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    "When your phone is busy or unanswered, Vi will forward calls to your AI receptionist virtual number (ExoPhone).",
                    fontSize = 13.sp,
                    color = Color(0xFFCBD5E1),
                    lineHeight = 18.sp
                )

                OutlinedTextField(
                    value = exoPhone,
                    onValueChange = { exoPhone = it },
                    label = { Text("ExoPhone Number") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        focusedBorderColor = Color(0xFF38BDF8),
                        unfocusedBorderColor = DarkSurfaceVariant
                    )
                )

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(10.dp))
                        .background(DarkBackground)
                        .padding(12.dp)
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(
                            text = "Conditional Forwarding USSD Code:",
                            fontSize = 11.sp,
                            color = Color(0xFF64748B)
                        )
                        Text(
                            text = "*61*$exoPhone#",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF38BDF8)
                        )
                        Text(
                            text = "Deactivation Code: ##61#",
                            fontSize = 11.sp,
                            color = Color(0xFF94A3B8)
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val encoded = Uri.encode("*61*$exoPhone#")
                    val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:$encoded"))
                    context.startActivity(intent)
                    onDismiss()
                },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB))
            ) {
                Text("Open Dialer (*61*)", color = Color.White)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Close", color = Color(0xFF64748B))
            }
        }
    )
}

@Composable
fun ServerSettingsDialog(
    currentUrl: String,
    onDismiss: () -> Unit,
    onSaveUrl: (String) -> Unit
) {
    var urlInput by remember { mutableStateOf(currentUrl) }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = {
            Text(
                "⚙️ Backend Server Settings",
                color = Color(0xFFF8FAFC),
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    "Set the FastAPI base URL to connect the dashboard to your running server:",
                    fontSize = 12.sp,
                    color = Color(0xFF94A3B8)
                )

                OutlinedTextField(
                    value = urlInput,
                    onValueChange = { urlInput = it },
                    label = { Text("Base URL") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        focusedBorderColor = Color(0xFF38BDF8),
                        unfocusedBorderColor = DarkSurfaceVariant
                    )
                )

                Text(
                    "Quick Presets:",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF64748B)
                )

                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        SuggestionChip(
                            onClick = { urlInput = "http://10.136.201.17:8000/" },
                            label = { Text("PC Wi-Fi (10.136.201.17)", fontSize = 11.sp) },
                            colors = SuggestionChipDefaults.suggestionChipColors(labelColor = Color(0xFF22C55E))
                        )
                        SuggestionChip(
                            onClick = { urlInput = "http://10.0.2.2:8000/" },
                            label = { Text("Emulator", fontSize = 11.sp) },
                            colors = SuggestionChipDefaults.suggestionChipColors(labelColor = Color(0xFF38BDF8))
                        )
                    }
                    Text(
                        "Tip: Connect phone to same Wi-Fi as PC (10.136.201.17:8000), or deploy backend to cloud (Render/Railway) for 24/7 public access.",
                        fontSize = 11.sp,
                        color = Color(0xFF64748B)
                    )
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    onSaveUrl(urlInput)
                    onDismiss()
                },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB))
            ) {
                Text("Save & Connect", color = Color.White)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel", color = Color(0xFF64748B))
            }
        }
    )
}
