#!/usr/bin/env python3
"""
INDAGO Evidence Capture Platform
Create default admin user
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")

from app.core.database import AsyncSessionLocal, init_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from sqlalchemy import select


async def create_admin():
    await init_db()

    async with AsyncSessionLocal() as db:
        # Check if admin exists
        result = await db.execute(select(User).where(User.username == "admin"))
        existing = result.scalar_one_or_none()

        if existing:
            print("Admin user already exists.")
            return

        admin = User(
            email="admin@indago.local",
            username="admin",
            full_name="INDAGO Administrator",
            hashed_password=get_password_hash("IndagoAdmin2024!"),
            role=UserRole.ADMINISTRATOR,
            organization="INDAGO",
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        print("Admin user created:")
        print("  Username: admin")
        print("  Password: IndagoAdmin2024!")
        print("  Role: administrator")

        # Create demo investigator
        investigator = User(
            email="investigator@indago.local",
            username="investigator",
            full_name="Demo Investigator",
            hashed_password=get_password_hash("Investigator2024!"),
            role=UserRole.INVESTIGATOR,
            organization="Digital Forensics Unit",
            badge_number="DFU-001",
            is_active=True,
        )
        db.add(investigator)
        await db.commit()
        print("\nDemo investigator created:")
        print("  Username: investigator")
        print("  Password: Investigator2024!")


if __name__ == "__main__":
    asyncio.run(create_admin())
