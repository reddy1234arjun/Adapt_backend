# 🛒 E-Commerce Backend API

This is a backend service for an E-Commerce platform built with **FastAPI** and **SQLAlchemy**. It includes core features like admin and user management, authentication with JWT, role-based access control, and product/stock handling.

---

## ✅ Features

### 🔐 Authentication & Authorization
- User registration and login using JWT
- Admin registration endpoint (restricted)
- Secure password hashing with Bcrypt
- Role-based access (Admin, User)
- Token validation and role authorization middleware

### 👤 User & Role Management
- Separate tables for:
  - Users
  - Roles (Admin, User, etc.)
- Unique user-role linkage
- Login status and attempt tracking

### 📦 Product Management
- `Category` Table
  - Main product categories
- `SubCategory` Table
  - Linked to Category
- `Product` Table
  - Product name, description, pricing, stock reference
- `Stock` Table
  - Track available quantity per product
  - Can be updated after purchase or restocking

---

## 🛠️ Tech Stack

- **Backend Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Authentication:** JWT + Bcrypt
- **Validation:** Pydantic
- **Environment Variables:** `dotenv`
- **Migrations:** Alembic

---

Method	Endpoint	Description
POST	/admin/register	Admin registration (restricted)
POST	/auth/register	User registration
POST	/auth/login	User login with JWT
GET	/users/me	Get current user
GET	/roles/	List roles
POST	/categories/	Create category
GET	/categories/	List categories
POST	/subcategories/	Create subcategory
GET	/subcategories/	List subcategories
POST	/products/	Create product
GET	/products/	List products
POST	/stock/	Add/Update stock
GET	/stock/{product_id}	Get stock for product

💡 Swagger UI available at /docs



