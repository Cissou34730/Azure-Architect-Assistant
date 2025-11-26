"""
Data migration script from old TypeScript backend schema to new Python backend schema.
Migrates projects, documents, states, and messages while preserving all data.
"""

import sqlite3
import asyncio
import logging
import json
from pathlib import Path
from datetime import datetime

from app.database import AsyncSessionLocal, init_database
from app.models import Project, ProjectDocument, ProjectState, ConversationMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
OLD_DB_PATH = PROJECT_ROOT / "data" / "projects.db"
NEW_DB_PATH = PROJECT_ROOT / "data" / "projects_new.db"
BACKUP_DB_PATH = PROJECT_ROOT / "data" / "projects_backup.db"


def backup_old_database():
    """Create a backup of the old database."""
    if OLD_DB_PATH.exists():
        import shutil
        shutil.copy(OLD_DB_PATH, BACKUP_DB_PATH)
        logger.info(f"✓ Created backup at: {BACKUP_DB_PATH}")
    else:
        logger.error(f"Old database not found at: {OLD_DB_PATH}")
        raise FileNotFoundError("Old database not found")


def examine_old_schema():
    """Examine the old database schema."""
    conn = sqlite3.connect(OLD_DB_PATH)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    logger.info("=" * 60)
    logger.info("OLD DATABASE SCHEMA:")
    logger.info("=" * 60)
    
    for table in tables:
        table_name = table[0]
        logger.info(f"\n📋 Table: {table_name}")
        
        # Get table info
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        for col in columns:
            logger.info(f"  - {col[1]} ({col[2]})")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        logger.info(f"  📊 Rows: {count}")
    
    logger.info("=" * 60)
    conn.close()


def read_old_data():
    """Read all data from the old database."""
    conn = sqlite3.connect(OLD_DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    cursor = conn.cursor()
    
    # Read projects
    cursor.execute("SELECT * FROM projects")
    projects = [dict(row) for row in cursor.fetchall()]
    logger.info(f"📦 Found {len(projects)} projects")
    
    # Read documents - OLD SCHEMA HAS DIFFERENT COLUMN NAMES
    cursor.execute("SELECT * FROM documents")
    documents_raw = cursor.fetchall()
    documents = []
    for row in documents_raw:
        # Map old schema to expected schema
        doc = {
            'id': row['id'],
            'projectId': row['projectId'],
            'fileName': row['filename'],  # OLD: filename -> NEW: fileName
            'mimeType': 'text/plain',  # Default, wasn't stored in old schema
            'rawText': row['content'],  # OLD: content -> NEW: rawText
            'uploadedAt': row['uploadedAt']
        }
        documents.append(doc)
    logger.info(f"📄 Found {len(documents)} documents")
    
    # Read project states
    cursor.execute("SELECT * FROM project_states")
    states = [dict(row) for row in cursor.fetchall()]
    logger.info(f"📊 Found {len(states)} project states")
    
    # Read messages
    cursor.execute("SELECT * FROM messages")
    messages = [dict(row) for row in cursor.fetchall()]
    logger.info(f"💬 Found {len(messages)} messages")
    
    conn.close()
    
    return {
        'projects': projects,
        'documents': documents,
        'states': states,
        'messages': messages
    }


async def migrate_data(old_data, session_maker):
    """Migrate data to the new schema using provided session maker."""
    logger.info("=" * 60)
    logger.info("STARTING DATA MIGRATION")
    logger.info("=" * 60)
    
    async with session_maker() as session:
        try:
            # Migrate projects
            logger.info("\n📦 Migrating projects...")
            for proj_data in old_data['projects']:
                project = Project(
                    id=proj_data['id'],
                    name=proj_data['name'],
                    text_requirements=proj_data.get('textRequirements'),  # Camel case in old schema
                    created_at=proj_data['createdAt']
                )
                session.add(project)
                logger.info(f"  ✓ Migrated project: {project.name} ({project.id})")
            
            await session.flush()
            logger.info(f"✓ Migrated {len(old_data['projects'])} projects")
            
            # Migrate documents
            logger.info("\n📄 Migrating documents...")
            for doc_data in old_data['documents']:
                document = ProjectDocument(
                    id=doc_data['id'],
                    project_id=doc_data['projectId'],
                    file_name=doc_data['fileName'],
                    mime_type=doc_data['mimeType'],
                    raw_text=doc_data['rawText'],
                    uploaded_at=doc_data['uploadedAt']
                )
                session.add(document)
            
            await session.flush()
            logger.info(f"✓ Migrated {len(old_data['documents'])} documents")
            
            # Migrate project states
            logger.info("\n📊 Migrating project states...")
            for state_data in old_data['states']:
                # State is already JSON string in old schema
                state = ProjectState(
                    project_id=state_data['projectId'],
                    state=state_data['state'],
                    updated_at=state_data['updatedAt']
                )
                session.add(state)
            
            await session.flush()
            logger.info(f"✓ Migrated {len(old_data['states'])} project states")
            
            # Migrate messages
            logger.info("\n💬 Migrating messages...")
            for msg_data in old_data['messages']:
                message = ConversationMessage(
                    id=msg_data['id'],
                    project_id=msg_data['projectId'],
                    role=msg_data['role'],
                    content=msg_data['content'],
                    timestamp=msg_data['timestamp'],
                    waf_sources=msg_data.get('wafSources')  # Already JSON string or NULL
                )
                session.add(message)
            
            await session.flush()
            logger.info(f"✓ Migrated {len(old_data['messages'])} messages")
            
            # Commit all changes
            await session.commit()
            
            logger.info("=" * 60)
            logger.info("✅ MIGRATION COMPLETE!")
            logger.info("=" * 60)
            logger.info(f"  Projects: {len(old_data['projects'])}")
            logger.info(f"  Documents: {len(old_data['documents'])}")
            logger.info(f"  States: {len(old_data['states'])}")
            logger.info(f"  Messages: {len(old_data['messages'])}")
            logger.info("=" * 60)
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Migration failed: {e}")
            raise


async def verify_migration(session_maker):
    """Verify the migrated data."""
    logger.info("\n🔍 Verifying migration...")
    
    from sqlalchemy import select
    
    async with session_maker() as session:
        # Count projects
        result = await session.execute(select(Project))
        projects = result.scalars().all()
        logger.info(f"  ✓ Projects in new DB: {len(projects)}")
        
        # Count documents
        result = await session.execute(select(ProjectDocument))
        documents = result.scalars().all()
        logger.info(f"  ✓ Documents in new DB: {len(documents)}")
        
        # Count states
        result = await session.execute(select(ProjectState))
        states = result.scalars().all()
        logger.info(f"  ✓ States in new DB: {len(states)}")
        
        # Count messages
        result = await session.execute(select(ConversationMessage))
        messages = result.scalars().all()
        logger.info(f"  ✓ Messages in new DB: {len(messages)}")
        
        # Show first project details
        if projects:
            proj = projects[0]
            logger.info(f"\n📋 Sample project: {proj.name}")
            logger.info(f"   ID: {proj.id}")
            logger.info(f"   Created: {proj.created_at}")
            logger.info(f"   Has requirements: {bool(proj.text_requirements)}")


async def main():
    """Main migration process."""
    logger.info("🚀 Starting database migration...")
    logger.info(f"   Old DB: {OLD_DB_PATH}")
    logger.info(f"   New DB: {NEW_DB_PATH}")
    
    try:
        # Step 1: Backup
        logger.info("\n📋 Step 1: Creating backup...")
        backup_old_database()
        
        # Step 2: Examine old schema
        logger.info("\n📋 Step 2: Examining old schema...")
        examine_old_schema()
        
        # Step 3: Read old data
        logger.info("\n📋 Step 3: Reading old data...")
        old_data = read_old_data()
        
        # Step 4: Remove new DB if exists
        logger.info("\n📋 Step 4: Preparing new database...")
        if NEW_DB_PATH.exists():
            NEW_DB_PATH.unlink()
            logger.info("  ✓ Removed existing new database")
        
        # Step 5: Initialize new database schema (to NEW location)
        logger.info("\n📋 Step 5: Initializing new database schema...")
        # Create engine and session for new database
        from app import database
        from app.models.project import Base
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from sqlalchemy.pool import StaticPool
        
        new_engine = create_async_engine(
            f"sqlite+aiosqlite:///{NEW_DB_PATH}",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )
        
        # Create all tables using Base metadata
        async with new_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session factory for this database
        NewSessionLocal = async_sessionmaker(
            new_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info(f"  ✓ New database created at: {NEW_DB_PATH}")
        
        # Step 6: Migrate data
        logger.info("\n📋 Step 6: Migrating data to new schema...")
        await migrate_data(old_data, NewSessionLocal)
        
        # Step 7: Verify migration
        logger.info("\n📋 Step 7: Verifying migration...")
        await verify_migration(NewSessionLocal)
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 MIGRATION SUCCESSFUL!")
        logger.info("=" * 60)
        logger.info(f"✅ Backup saved at: {BACKUP_DB_PATH}")
        logger.info(f"✅ New database created at: {NEW_DB_PATH}")
        logger.info("")
        logger.info("📝 MANUAL STEPS REQUIRED:")
        logger.info("   1. Close any programs accessing projects.db")
        logger.info("   2. Delete or rename: projects.db")
        logger.info("   3. Rename: projects_new.db → projects.db")
        logger.info("   4. Start the Python backend")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        logger.error("The backup is available if you need to restore.")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
