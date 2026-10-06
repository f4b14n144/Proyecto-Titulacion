from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # IA vía LiteLLM — ver la cabecera de services/ia_engine.py
    AI_MODEL: str = "groq/openai/gpt-oss-120b"
    AI_PARAMS: str = ""             # JSON con parámetros extra para litellm
    AI_MAX_TOKENS_EXTRA: int = 0    # margen para modelos que razonan
    AI_PROVIDER: str = ""           # obsoleto: el proveedor va en el prefijo de AI_MODEL
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""

    # ── Interruptor global de correo ──────────────────────────────────────────
    # Con MAIL_MODO_PRUEBA=true NINGÚN correo llega a su destinatario real. Se
    # aplica dentro de `mail_service.enviar_email`, o sea en la capa más baja: así
    # ningún camino puede saltárselo, ni siquiera los envíos automáticos del
    # planificador (que es justo por donde se escapan los accidentes).
    #   - Si hay MAIL_REDIRECT_TO, todo se redirige a esa dirección.
    #   - Si no la hay, no se envía nada: solo se registra en el log.
    MAIL_MODO_PRUEBA: bool = False
    MAIL_REDIRECT_TO: str = ""


    APP_NAME: str = "Sistema Informes UPS"
    ENVIRONMENT: str = "development"

    # URL pública del sistema. Se usa en los correos para enlazar al panel donde
    # el docente registra sus observaciones. En producción, el dominio real
    # (p. ej. https://informes.ups.edu.ec).
    APP_URL: str = "http://localhost"

    # Orígenes permitidos por CORS, separados por comas.
    # En producción hay que poner el dominio real (p. ej. https://informes.ups.edu.ec).
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost"

    @property
    def es_produccion(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def origenes_cors(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
