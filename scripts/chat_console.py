import os
import sys
import uuid
from typing import Optional

# Add project root to path to allow imports from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.presentation.http.dependencies import (
    reset_state,
    get_respond_to_message_use_case,
)
from app.application.dto.respond_to_message_dto import RespondToMessageRequest


def load_dotenv():
    """Simple .env loader if python-dotenv is not installed."""
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
    )
    if os.path.exists(env_path):
        print(f"Loading environment from {env_path}")
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Remove quotes if present
                    value = value.strip("'").strip('"')
                    os.environ[key] = value


def run_chat():
    load_dotenv()

    # Initialize dependencies (DB, LLM, etc.)
    print("Iniciando estado de la aplicación...")
    reset_state()

    use_case = get_respond_to_message_use_case()

    tenant_id = os.getenv("DEFAULT_TENANT_ID", "nails-studio-ec")
    user_id = "console-user"
    channel = "console"
    conversation_id: Optional[uuid.UUID] = None

    print("=" * 50)
    print("Chatbot de Reservas - Modo Consola")
    print(f"Tenant: {tenant_id}")
    print("Escribe 'salir' o 'exit' para finalizar.")
    print("=" * 50)

    while True:
        try:
            message = input("\nUsuario > ")
            if message.lower() in ["salir", "exit"]:
                break

            if not message.strip():
                continue

            request = RespondToMessageRequest(
                tenant_id=tenant_id,
                user_id=user_id,
                channel=channel,
                message=message,
                conversation_id=conversation_id,
            )

            response = use_case.execute(request)
            conversation_id = response.conversation_id

            print(f"\nAI > {response.reply}")

            # Display options if any
            if response.response and response.response.options:
                print("\nOpciones:")
                for opt in response.response.options:
                    print(f"  - [{opt.id}] {opt.label}")

            # Display confirmation/cancel labels if any
            if response.response and (
                response.response.confirm_label or response.response.cancel_label
            ):
                confirm = response.response.confirm_label or "Confirmar"
                cancel = response.response.cancel_label or "Cancelar"
                print(f"\n[{confirm}] / [{cancel}]")

        except KeyboardInterrupt:
            print("\nSaliendo...")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    run_chat()
