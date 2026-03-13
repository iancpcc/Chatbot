#!/usr/bin/env bash
set -euo pipefail

# End-to-end conversational workflow test for "Manicure"
# Requires: curl, jq
#
# Usage:
#   bash scripts/chat_flow_manicure.sh
#
# Optional env vars:
#   BASE_URL=http://127.0.0.1:8000
#   TENANT_ID=demo-salon
#   USER_ID=user-1
#   API_KEY=your_api_key

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
TENANT_ID="${TENANT_ID:-demo-salon}"
USER_ID="${USER_ID:-user-1}"
CHANNEL="web"
API_KEY="${API_KEY:-}"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required"
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required"
  exit 1
fi

AUTH_ARGS=()
if [[ -n "$API_KEY" ]]; then
  AUTH_ARGS+=(-H "x-api-key: $API_KEY")
fi

api_post() {
  local path="$1"
  local payload="$2"
  curl -sS -X POST "$BASE_URL$path" \
    -H "Content-Type: application/json" \
    "${AUTH_ARGS[@]}" \
    -d "$payload"
}

print_step() {
  local title="$1"
  local response="$2"
  echo ""
  echo "=== $title ==="
  echo "$response" | jq
}

# 0) Setup demo entities for this tenant.
SERVICE_JSON="$(api_post "/v1/services" "$(jq -nc \
  --arg tenant "$TENANT_ID" \
  --arg name "Manicure" \
  '{tenant_id:$tenant,name:$name,duration_minutes:45,price:25.0}')")"
SERVICE_ID="$(echo "$SERVICE_JSON" | jq -r '.service_id')"

RESOURCE_JSON="$(api_post "/v1/resources" "$(jq -nc \
  --arg tenant "$TENANT_ID" \
  --arg name "Sala 1" \
  '{tenant_id:$tenant,name:$name}')")"
RESOURCE_ID="$(echo "$RESOURCE_JSON" | jq -r '.resource_id')"

echo "Prepared service_id=$SERVICE_ID"
echo "Prepared resource_id=$RESOURCE_ID"

# 1) Start conversation.
R1="$(api_post "/v1/chat" "$(jq -nc \
  --arg tenant "$TENANT_ID" \
  --arg user "$USER_ID" \
  --arg channel "$CHANNEL" \
  --arg message "hola" \
  '{tenant_id:$tenant,user_id:$user,channel:$channel,message:$message}')")"
print_step "Step 1 - Start" "$R1"
CONV_ID="$(echo "$R1" | jq -r '.conversation_id')"

# 2) Choose booking flow.
R2="$(api_post "/v1/chat" "$(jq -nc \
  --arg tenant "$TENANT_ID" \
  --arg user "$USER_ID" \
  --arg channel "$CHANNEL" \
  --arg conv "$CONV_ID" \
  --arg action "booking" \
  '{tenant_id:$tenant,user_id:$user,channel:$channel,conversation_id:$conv,message:"",action_id:$action}')")"
print_step "Step 2 - Choose booking" "$R2"

# 3) Choose Manicure service.
R3="$(api_post "/v1/chat" "$(jq -nc \
  --arg tenant "$TENANT_ID" \
  --arg user "$USER_ID" \
  --arg channel "$CHANNEL" \
  --arg conv "$CONV_ID" \
  --arg action "$SERVICE_ID" \
  '{tenant_id:$tenant,user_id:$user,channel:$channel,conversation_id:$conv,message:"",action_id:$action}')")"
print_step "Step 3 - Select service" "$R3"

# 4) Choose resource.
R4="$(api_post "/v1/chat" "$(jq -nc \
  --arg tenant "$TENANT_ID" \
  --arg user "$USER_ID" \
  --arg channel "$CHANNEL" \
  --arg conv "$CONV_ID" \
  --arg action "$RESOURCE_ID" \
  '{tenant_id:$tenant,user_id:$user,channel:$channel,conversation_id:$conv,message:"",action_id:$action}')")"
print_step "Step 4 - Select resource" "$R4"

# 5) Choose first suggested slot.
SLOT_ID="$(echo "$R4" | jq -r '.response.options[0].id')"
R5="$(api_post "/v1/chat" "$(jq -nc \
  --arg tenant "$TENANT_ID" \
  --arg user "$USER_ID" \
  --arg channel "$CHANNEL" \
  --arg conv "$CONV_ID" \
  --arg action "$SLOT_ID" \
  '{tenant_id:$tenant,user_id:$user,channel:$channel,conversation_id:$conv,message:"",action_id:$action}')")"
print_step "Step 5 - Select slot" "$R5"

# 6) Customer name.
R6="$(api_post "/v1/chat" "$(jq -nc \
  --arg tenant "$TENANT_ID" \
  --arg user "$USER_ID" \
  --arg channel "$CHANNEL" \
  --arg conv "$CONV_ID" \
  --arg message "nombre=Juan Perez" \
  '{tenant_id:$tenant,user_id:$user,channel:$channel,conversation_id:$conv,message:$message}')")"
print_step "Step 6 - Name" "$R6"

# 7) Customer contact.
R7="$(api_post "/v1/chat" "$(jq -nc \
  --arg tenant "$TENANT_ID" \
  --arg user "$USER_ID" \
  --arg channel "$CHANNEL" \
  --arg conv "$CONV_ID" \
  --arg message "contacto=666555444" \
  '{tenant_id:$tenant,user_id:$user,channel:$channel,conversation_id:$conv,message:$message}')")"
print_step "Step 7 - Contact" "$R7"

# 8) Confirm booking.
R8="$(api_post "/v1/chat" "$(jq -nc \
  --arg tenant "$TENANT_ID" \
  --arg user "$USER_ID" \
  --arg channel "$CHANNEL" \
  --arg conv "$CONV_ID" \
  --arg action "confirm" \
  '{tenant_id:$tenant,user_id:$user,channel:$channel,conversation_id:$conv,message:"confirmar",action_id:$action}')")"
print_step "Step 8 - Confirm" "$R8"

echo ""
echo "Flow completed."
