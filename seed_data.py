"""Seed script for populating the database with sample data"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal, init_db
from models import User, Band, Post, Follow, band_members, BandMemberRoleEnum
from security import hash_password
import uuid
from datetime import datetime, timezone


async def seed_database():
    """Seed the database with sample data"""
    print("Initializing database...")
    await init_db()
    
    async with AsyncSessionLocal() as db:
        print("Creating sample users...")
        
        # Create sample users
        users = [
            User(
                email="john.guitarist@example.com",
                hashed_password=hash_password("Password123"),
                display_name="John the Guitarist",
                bio="Rock guitarist with 10 years of experience",
                email_verified=True,
                instruments=["Guitar", "Bass"],
                genres=["Rock", "Blues"],
                location={"city": "Los Angeles", "country": "USA"}
            ),
            User(
                email="sarah.drummer@example.com",
                hashed_password=hash_password("Password123"),
                display_name="Sarah Drums",
                bio="Jazz drummer and music teacher",
                email_verified=True,
                instruments=["Drums", "Percussion"],
                genres=["Jazz", "Funk"],
                location={"city": "New York", "country": "USA"}
            ),
            User(
                email="mike.vocalist@example.com",
                hashed_password=hash_password("Password123"),
                display_name="Mike Voice",
                bio="Vocalist and songwriter",
                email_verified=True,
                instruments=["Vocals"],
                genres=["Pop", "Rock"],
                location={"city": "Nashville", "country": "USA"}
            ),
            User(
                email="lisa.pianist@example.com",
                hashed_password=hash_password("Password123"),
                display_name="Lisa Keys",
                bio="Classical and jazz pianist",
                email_verified=True,
                instruments=["Piano", "Keyboard"],
                genres=["Classical", "Jazz"],
                location={"city": "Chicago", "country": "USA"}
            )
        ]
        
        for user in users:
            db.add(user)
        
        await db.commit()
        for user in users:
            await db.refresh(user)
        
        print(f"Created {len(users)} users")
        
        # Create follows
        print("Creating follow relationships...")
        follows = [
            Follow(follower_id=users[0].id, following_id=users[1].id),
            Follow(follower_id=users[0].id, following_id=users[2].id),
            Follow(follower_id=users[1].id, following_id=users[0].id),
            Follow(follower_id=users[2].id, following_id=users[3].id),
        ]
        
        for follow in follows:
            db.add(follow)
        
        await db.commit()
        print(f"Created {len(follows)} follow relationships")
        
        # Create sample bands
        print("Creating sample bands...")
        bands = [
            Band(
                name="The Rock Stars",
                description="High-energy rock band",
                owner_id=users[0].id,
                genres=["Rock", "Alternative"],
                location={"city": "Los Angeles", "country": "USA"}
            ),
            Band(
                name="Jazz Fusion Collective",
                description="Experimental jazz fusion",
                owner_id=users[1].id,
                genres=["Jazz", "Fusion"],
                location={"city": "New York", "country": "USA"}
            )
        ]
        
        for band in bands:
            db.add(band)
        
        await db.commit()
        for band in bands:
            await db.refresh(band)
        
        print(f"Created {len(bands)} bands")
        
        # Add band members
        print("Adding band members...")
        stmt = band_members.insert().values(
            band_id=bands[0].id,
            user_id=users[0].id,
            role=BandMemberRoleEnum.OWNER
        )
        await db.execute(stmt)
        
        stmt = band_members.insert().values(
            band_id=bands[0].id,
            user_id=users[2].id,
            role=BandMemberRoleEnum.MEMBER
        )
        await db.execute(stmt)
        
        stmt = band_members.insert().values(
            band_id=bands[1].id,
            user_id=users[1].id,
            role=BandMemberRoleEnum.OWNER
        )
        await db.execute(stmt)
        
        await db.commit()
        print("Band members added")
        
        # Create sample posts
        print("Creating sample posts...")
        posts = [
            Post(
                author_id=users[0].id,
                title="New Guitar Riff!",
                content="Just composed this awesome riff. Check it out!",
                visibility="public"
            ),
            Post(
                author_id=users[1].id,
                content="Amazing jam session today with the band!",
                visibility="public"
            ),
            Post(
                author_id=users[0].id,
                band_id=bands[0].id,
                title="Upcoming Gig!",
                content="We're playing at The Music Hall next Friday. Come join us!",
                visibility="public"
            ),
            Post(
                author_id=users[2].id,
                content="Working on some new vocal techniques",
                visibility="followers"
            ),
        ]
        
        for post in posts:
            db.add(post)
        
        await db.commit()
        print(f"Created {len(posts)} posts")
        
        print("\n" + "="*50)
        print("Database seeded successfully!")
        print("="*50)
        print("\nSample login credentials:")
        print("Email: john.guitarist@example.com")
        print("Password: Password123")
        print("\nEmail: sarah.drummer@example.com")
        print("Password: Password123")
        print("="*50)


if __name__ == "__main__":
    asyncio.run(seed_database())
