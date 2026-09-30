import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from core.permissions import IsAdmin
from llm_sidecar.client import call_groq

logger = logging.getLogger("acuvera.admin_insight")

class AdminInsightChatView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        prompt = request.data.get("prompt", "")
        context = request.data.get("context", "")
        
        if not prompt:
            return Response({"error": "Prompt is required"}, status=400)

        system_prompt = (
            "You are the Acuvera Operations Chief AI interface. "
            "You have access to current hospital real-time metrics, overview data, starvation, and predicted bottlenecks. "
            "CRITICAL: In this context, 'starvation' or 'starving' refers exclusively to patients who have breached their maximum allowed waiting time SLA without seeing a doctor. IT DOES NOT MEAN LACK OF FOOD OR HYDRATION. "
            "The user is a hospital administrator. Use the provided context to answer their query. "
            "Keep the response concise, authoritative, and actionable. "
            "Do not hallucinate external metrics. Rely strictly on the provided JSON data. "
            "Format the response clearly using markdown bullet points for readability. "
            "Here is the real-time context from the ER:\n"
            f"---CONTEXT---\n{context}\n---END CONTEXT---"
        )
        
        feature_flags = request.feature_flags if hasattr(request, 'feature_flags') else {"LLM_ENABLED": True}

        # Use our groq client
        try:
            response_text = call_groq(
               system_prompt=system_prompt,
               user_content=prompt,
               feature_flags=feature_flags,
               max_tokens=800
            )

            # fallback if LLM is not configured properly or times out
            if not response_text:
                import json
                try:
                    ctx_obj = json.loads(context)
                    p_lower = prompt.lower()
                    
                    if "wait" in p_lower or "queue" in p_lower or "long" in p_lower:
                        response_text = (
                            "⏱️ **Wait Time Analysis**\n\n"
                            f"The current average wait time is **{ctx_obj.get('avg_wait_minutes', 0)} mins**.\n"
                            f"Our system estimates the overall queue load as **{ctx_obj.get('queue_load', 'Normal')}**."
                        )
                    elif "starv" in p_lower or "critical" in p_lower or "alert" in p_lower or "urgent" in p_lower:
                        response_text = (
                            "🚨 **Starvation & Critical Alerts**\n\n"
                            f"There are currently **{ctx_obj.get('starving_cases', 0)}** starvation alerts in the system, and **{ctx_obj.get('critical_cases', 0)}** critical cases overall.\n\n"
                            "Please ensure these cases are expedited immediately!"
                        )
                    elif "doctor" in p_lower or "staff" in p_lower or "utilization" in p_lower or "busy" in p_lower:
                        response_text = (
                            "👨‍⚕️ **Staff Utilization**\n\n"
                            f"Current doctor utilization is running at **{ctx_obj.get('doctor_utilization', 0)}%**."
                        )
                    elif "patient" in p_lower or "active" in p_lower or "how many" in p_lower:
                        response_text = (
                            "🏥 **Active Patient Volume**\n\n"
                            f"There are **{ctx_obj.get('active_patients', 0)}** patients currently active in the Emergency Department."
                        )
                    elif "give me a quick " in p_lower or "summary" in p_lower or "overview" in p_lower:
                        response_text = (
                            "**Hospital Operations Summary**\n\n"
                            f"• **Active Patients:** {ctx_obj.get('active_patients', 0)}\n"
                            f"• **Critical Cases:** {ctx_obj.get('critical_cases', 0)}\n"
                            f"• **Starvation Alerts:** {ctx_obj.get('starving_cases', 0)}\n"
                            f"• **Average Wait:** {ctx_obj.get('avg_wait_minutes', 0)} mins ({ctx_obj.get('queue_load', 'Normal')})\n"
                            f"• **Doctor Utilization:** {ctx_obj.get('doctor_utilization', 0)}%\n\n"
                            "*Note: Connecting to local deterministic telemetry.*"
                        )
                    else:
                        response_text = (
                            "I'm currently running in offline deterministic mode, but I can still answer specific questions about:\n"
                            "- Wait times and queue loads\n"
                            "- Starvation and critical alerts\n"
                            "- Doctor utilization\n"
                            "- Active patient volume\n"
                            "What would you like to know?"
                        )
                except Exception:
                    response_text = "I am currently unable to connect to the intelligence layer. Please review the critical starvation alerts and act accordingly."
        except Exception as e:
            logger.error("Admin insight exception: %s", e)
            response_text = "Error reaching the AI service. Please try again."

        # Ensure the AI asks the user how to help at the end of the first message
        if prompt.lower() == "give me a quick summary of the current hospital situation.":
            response_text += "\n\nIs there anything else I can help you with today?"

        return Response({"data": {"answer": response_text}})
