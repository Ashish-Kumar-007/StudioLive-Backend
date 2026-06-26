# 🎬 StudioLive Backend

A robust, secure, and scalable NestJS backend for managing a media production studio workflow.

## 🚀 Quick Start

### 1. Installation
```bash
npm install
```

### 2. Environment Setup
Create a `.env` file in the root directory and add your Supabase credentials:
```env
DATABASE_URL="your_direct_connection_url"
DIRECT_URL="your_direct_connection_url"
SUPABASE_URL="your_project_url"
SUPABASE_KEY="your_anon_key"
SUPABASE_JWT_SECRET="your_jwt_secret"
SUPABASE_SERVICE_ROLE_KEY="your_service_role_key"
```

### 3. Database Sync
```bash
npx prisma generate
npx prisma migrate dev
```

### 4. Bootstrap Admin
```bash
npx ts-node src/seed-admin.ts
```

### 5. Run Server
```bash
npm run start:dev
```

## 🛠 Tech Stack
- **Framework**: NestJS 11
- **Database**: PostgreSQL (Supabase)
- **ORM**: Prisma 7 (Driver Adapter Pattern)
- **Auth**: Supabase Auth (JWKS / RS256)
- **Validation**: Class Validator & DTOs

## 📖 API Documentation
For a full list of all 20+ endpoints, roles, and example payloads, please refer to:
👉 **[API_GUIDE.md](./API_GUIDE.md)**

## 📁 Project Structure
- `src/auth`: Supabase integration and JWT strategies.
- `src/users`: User registration and RBAC.
- `src/leads`: Lead collection and qualification.
- `src/tasks`: Production task management.
- `src/reporting`: Financial and performance analytics.
- `prisma/schema.prisma`: Database models.

## ⚖️ License
MIT
