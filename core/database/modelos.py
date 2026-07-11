# core/database/models.py
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    Text, ForeignKey, JSON, Enum, BigInteger, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database.connection import Base
import enum
from datetime import datetime

class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    DELETED = "deleted"

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    EXPIRED = "expired"

class PaymentMethod(str, enum.Enum):
    PIX = "pix"
    CREDIT_CARD = "credit_card"
    BOLETO = "boleto"

class FormFieldType(str, enum.Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    FILE = "file"
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    SELECT = "select"
    MULTIPLE_CHOICE = "multiple_choice"

class User(Base):
    """Modelo de usuário/cliente"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language = Column(String(10), default="pt")
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    balance = Column(Float, default=0.0)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    source = Column(String(50), nullable=True)  # Origem do cadastro
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    last_access = Column(DateTime, nullable=True)
    
    # Relacionamentos
    orders = relationship("Order", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    form_responses = relationship("FormResponse", back_populates="user")
    
    __table_args__ = (
        Index('idx_user_telegram_id', 'telegram_id'),
        Index('idx_user_status', 'status'),
    )

class Category(Base):
    """Categorias de produtos"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image = Column(String(500), nullable=True)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relacionamentos
    products = relationship("Product", back_populates="category")
    children = relationship("Category", backref="parent", remote_side=[id])
    
    __table_args__ = (
        Index('idx_category_active', 'is_active'),
    )

class Product(Base):
    """Produtos/Serviços"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    promotional_price = Column(Float, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    images = Column(JSON, default=[])  # Lista de URLs
    videos = Column(JSON, default=[])  # Lista de URLs
    benefits = Column(JSON, default=[])  # Lista de benefícios
    stock = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relacionamentos
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    
    __table_args__ = (
        Index('idx_product_active', 'is_active'),
        Index('idx_product_featured', 'is_featured'),
        Index('idx_product_category', 'category_id'),
    )

class Plan(Base):
    """Planos de assinatura/pacotes"""
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    benefits = Column(JSON, default=[])
    products_included = Column(JSON, default=[])  # IDs dos produtos inclusos
    services_included = Column(JSON, default=[])  # Lista de serviços
    warranty = Column(String(255), nullable=True)  # Garantia
    validity_days = Column(Integer, nullable=True)  # Dias de validade
    image = Column(String(500), nullable=True)
    observations = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    __table_args__ = (
        Index('idx_plan_active', 'is_active'),
    )

class Order(Base):
    """Pedidos"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    total_amount = Column(Float, nullable=False)
    discount = Column(Float, default=0.0)
    final_amount = Column(Float, nullable=False)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    paid_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Relacionamentos
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")
    payments = relationship("Payment", back_populates="order")
    
    __table_args__ = (
        Index('idx_order_user', 'user_id'),
        Index('idx_order_status', 'status'),
        Index('idx_order_created', 'created_at'),
    )

class OrderItem(Base):
    """Itens do pedido"""
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    # Relacionamentos
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    plan = relationship("Plan")

class Payment(Base):
    """Pagamentos"""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(String(50), nullable=False)  # pending, approved, rejected, refunded
    external_id = Column(String(255), unique=True, nullable=True)  # ID do Mercado Pago
    pix_qr_code = Column(Text, nullable=True)
    pix_copy_paste = Column(Text, nullable=True)
    pix_expiration = Column(DateTime, nullable=True)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    approved_at = Column(DateTime, nullable=True)
    
    # Relacionamentos
    order = relationship("Order", back_populates="payments")
    user = relationship("User", back_populates="payments")
    
    __table_args__ = (
        Index('idx_payment_order', 'order_id'),
        Index('idx_payment_user', 'user_id'),
        Index('idx_payment_status', 'status'),
        Index('idx_payment_external', 'external_id'),
    )

class Form(Base):
    """Formulários personalizados"""
    __tablename__ = "forms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relacionamentos
    fields = relationship("FormField", back_populates="form", order_by="FormField.order")
    responses = relationship("FormResponse", back_populates="form")

class FormField(Base):
    """Campos dos formulários"""
    __tablename__ = "form_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    label = Column(String(255), nullable=False)
    field_type = Column(Enum(FormFieldType), nullable=False)
    required = Column(Boolean, default=False)
    options = Column(JSON, default=[])  # Para select/multiple_choice
    placeholder = Column(String(255), nullable=True)
    help_text = Column(String(500), nullable=True)
    order = Column(Integer, default=0)
    validation = Column(JSON, default={})  # Regras de validação
    
    # Relacionamentos
    form = relationship("Form", back_populates="fields")

class FormResponse(Base):
    """Respostas dos formulários"""
    __tablename__ = "form_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    responses = Column(JSON, default={})  # {field_id: value}
    created_at = Column(DateTime, server_default=func.now())
    
    # Relacionamentos
    form = relationship("Form", back_populates="responses")
    user = relationship("User", back_populates="form_responses")
    
    __table_args__ = (
        Index('idx_form_response_form', 'form_id'),
        Index('idx_form_response_user', 'user_id'),
    )

class Button(Base):
    """Botões dos menus"""
    __tablename__ = "buttons"
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String(255), nullable=False)
    callback_data = Column(String(255), unique=True, nullable=True)
    url = Column(String(500), nullable=True)
    emoji = Column(String(10), nullable=True)
    parent_id = Column(Integer, ForeignKey("buttons.id"), nullable=True)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    for_admin = Column(Boolean, default=False)  # Visível apenas para admin
    metadata = Column(JSON, default={})
    
    # Relacionamentos
    children = relationship("Button", backref="parent", remote_side=[id])

class Menu(Base):
    """Menus do bot"""
    __tablename__ = "menus"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    buttons = Column(JSON, default=[])  # IDs dos botões
    is_active = Column(Boolean, default=True)
    is_main = Column(Boolean, default=False)  # Menu principal
    order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

class AIConfig(Base):
    """Configurações da IA"""
    __tablename__ = "ai_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    model = Column(String(100), default="gpt-3.5-turbo")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=500)
    system_prompt = Column(Text, nullable=True)
    behavior = Column(Text, nullable=True)  # Instruções de comportamento
    is_active = Column(Boolean, default=True)
    daily_limit = Column(Integer, default=100)  # Limite diário de requisições
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class SystemLog(Base):
    """Logs do sistema"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)
    details = Column(JSON, default={})
    ip_address = Column(String(45), nullable=True)
    status = Column(String(50), nullable=True)  # success, error, warning
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_log_action', 'action'),
        Index('idx_log_created', 'created_at'),
        Index('idx_log_user', 'user_id'),
    )

class Notification(Base):
    """Notificações"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    type = Column(String(50), nullable=False)  # payment, order, system, alert
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_notification_user', 'user_id'),
        Index('idx_notification_read', 'is_read'),
    )

class AdminUser(Base):
    """Administradores do sistema"""
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    permissions = Column(JSON, default={})  # Permissões específicas
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_access = Column(DateTime, nullable=True)

class ChatHistory(Base):
    """Histórico de conversas"""
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    is_ai = Column(Boolean, default=False)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_chat_user', 'user_id'),
        Index('idx_chat_created', 'created_at'),
    )
