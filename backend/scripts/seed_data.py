import random
import sys
import os
from datetime import datetime, timedelta, timezone

# Add backend directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.user import User
from app.models.coordi import Coordi
from app.models.tag import Tag
from app.models.coordi_item import CoordiItem
from app.models.user_closet_item import UserClosetItem
from app.models.user_coordi_interaction import UserCoordiInteraction
from app.models.user_coordi_view_log import UserCoordiViewLog
from app.models.user_preferred_tag import UserPreferredTag
from app.core.security import hash_password

"""
추천팀을 위한 상호작용 데이터 제공

데이터 설명
- 총 400명의 가상 사용자
    - 코디 취향: 성별에 맞는 코디 5개를 랜덤으로 선택하여 선호(preference) 상호작용을 생성
    - 태그 취향: 성별에 따라 필터링된 태그(여성 1-18, 남성 19-25 + 공통) 중 3~10개를 랜덤으로 선택하여 UserPreferredTag에 저장

- 상호 작용(Interaction) 생성
    - 사용자의 성별에 맞는 코디만 노출
    - 사용자별로 선호 스타일(1~2개)을 배정하고, 노출되는 코디의 70%가 해당 스타일과 일치하도록 하여 일관성을 유지
    - 150~300개의 코디에 대해 like (10%의 확률) Skip (90%의 확률) 반응 생성
    - Cold-start에서 선택한 코디의 경우 preference 로 기록됨

- 시청 시간(View Log) 생성
    - like 는 5-30초
    - skip 은 1-5초
    - preference 는 시간이 따로 기록되지 않음

- 아이템 저장(Save)
    - 한 코디에 포함된 아이템 중 1-3개를 랜덤으로 선택해 UserClosetItem에 저장

생성된 데이터
- 사용자 (Users): 400명
- 상호작용 (Interactions): 7,857건
- 시청 로그 (View Logs): 7,357건
- 선호 태그 (Preferred Tags): 627건
- 저장된 아이템 (Closet Items): 1,194건
"""

def seed_data():
    db = SessionLocal()
    try:
        print("Starting data seeding...")

        # 1. Check for existing coordis
        coordi_count = db.execute(select(func.count(Coordi.coordi_id))).scalar()
        if coordi_count == 0:
            print("Error: No coordis found in database. Please run load_coordis.py first.")
            return

        print(f"Found {coordi_count} coordis.")

        # 2. Create Users
        print("Creating 400 users...")
        users = []
        for i in range(400):
            email = f"user{i+1}@example.com"
            # Check if user exists
            existing_user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if existing_user:
                users.append(existing_user)
                continue

            gender = random.choice(["male", "female"])
            user = User(
                email=email,
                password_hash=hash_password("password123"),
                name=f"User {i+1}",
                gender=gender,
                has_completed_onboarding=True
            )
            db.add(user)
            users.append(user)
        
        db.commit()
        # Refresh users to get IDs
        for user in users:
            db.refresh(user)
        
        print(f"Created/Loaded {len(users)} users.")

        # 2.5 Clear existing data for these users to apply new logic
        print("Clearing existing interactions for test users...")
        user_ids = [u.user_id for u in users]
        if user_ids:
            db.execute(delete(UserCoordiInteraction).where(UserCoordiInteraction.user_id.in_(user_ids)))
            db.execute(delete(UserCoordiViewLog).where(UserCoordiViewLog.user_id.in_(user_ids)))
            db.execute(delete(UserClosetItem).where(UserClosetItem.user_id.in_(user_ids)))
            db.execute(delete(UserPreferredTag).where(UserPreferredTag.user_id.in_(user_ids)))
            db.commit()

        # 3. Create Interactions & Tags
        print("Creating interactions and tags...")
        
        # Fetch all coordi IDs by gender to optimize random selection
        male_coordis = db.execute(select(Coordi.coordi_id, Coordi.style).where(Coordi.gender == 'male')).all()
        female_coordis = db.execute(select(Coordi.coordi_id, Coordi.style).where(Coordi.gender == 'female')).all()
        
        # Helper to filter by style
        def filter_by_style(coordis, styles):
            return [c.coordi_id for c in coordis if c.style in styles]

        # Tag definitions
        # Tag definitions: Fetch real tag IDs from DB
        all_tag_ids = db.execute(select(Tag.tag_id)).scalars().all()
        
        if not all_tag_ids:
            print("Error: No tags found in database. Please run load_tags.py first.")
            return

        # Simple logic: split tags or use all available tags randomly
        # Since we don't know exactly which ID maps to which concept without querying names,
        # we will use the available valid IDs for both genders to avoid FK errors.
        female_tag_ids = all_tag_ids 
        male_tag_ids = all_tag_ids

        interaction_count = 0
        view_log_count = 0
        tag_count = 0
        saved_item_count = 0

        for user in users:
            # 3.0 Preferred Tags (3-10 items)
            # Check if tags exist
            existing_tags_count = db.execute(
                select(func.count(UserPreferredTag.user_id)).where(UserPreferredTag.user_id == user.user_id)
            ).scalar()

            if existing_tags_count == 0:
                available_tags = male_tag_ids if user.gender == 'male' else female_tag_ids
                num_tags = random.randint(3, 10)
                selected_tags = random.sample(available_tags, k=min(num_tags, len(available_tags)))
                
                for tag_id in selected_tags:
                    pref_tag = UserPreferredTag(user_id=user.user_id, tag_id=tag_id)
                    db.add(pref_tag)
                    tag_count += 1

            # Track interactions and saved items for this user in this session
            current_user_interacted_ids = set()
            current_user_saved_item_ids = set()

            # 3.1 Cold-Start Preferences (5 items)
            # Select coordis matching user gender
            target_coordis = male_coordis if user.gender == 'male' else female_coordis
            target_coordi_ids = [c.coordi_id for c in target_coordis]
            
            if not target_coordi_ids:
                 # Fallback if no gender specific coordis
                 target_coordi_ids = [c.coordi_id for c in male_coordis + female_coordis]
            
            # Randomly select 5 for preference
            # Check existing preference count to avoid adding more if already seeded
            existing_pref_count = db.execute(
                select(func.count(UserCoordiInteraction.user_id)).where(
                    UserCoordiInteraction.user_id == user.user_id,
                    UserCoordiInteraction.action_type == "preference"
                )
            ).scalar()

            if existing_pref_count < 5:
                needed = 5 - existing_pref_count
                preference_coordis = random.sample(target_coordi_ids, k=min(needed, len(target_coordi_ids)))
                
                for coordi_id in preference_coordis:
                    # Double check existence
                    exists = db.execute(
                        select(UserCoordiInteraction).where(
                            UserCoordiInteraction.user_id == user.user_id,
                            UserCoordiInteraction.coordi_id == coordi_id
                        )
                    ).scalar_one_or_none()
                    
                    if not exists and coordi_id not in current_user_interacted_ids:
                        interaction = UserCoordiInteraction(
                            user_id=user.user_id,
                            coordi_id=coordi_id,
                            action_type="preference"
                        )
                        db.add(interaction)
                        interaction_count += 1
                        current_user_interacted_ids.add(coordi_id)

            # 3.2 Browsing Interactions (50-100 items)
            # Check existing interactions to avoid over-seeding on re-runs
            existing_interaction_count = db.execute(
                select(func.count(UserCoordiInteraction.user_id)).where(
                    UserCoordiInteraction.user_id == user.user_id,
                    UserCoordiInteraction.action_type.in_(["like", "skip"])
                )
            ).scalar()

            if existing_interaction_count < 150:
                # Style Consistency: Pick 1-2 preferred styles
                all_styles = list(set([c.style for c in target_coordis]))
                preferred_styles = random.sample(all_styles, k=min(2, len(all_styles)))
                
                # Filter candidates by gender (already done in target_coordis)
                # Get all interacted coordis for this user to exclude (from DB)
                interacted_coordis_db = db.execute(
                    select(UserCoordiInteraction.coordi_id).where(UserCoordiInteraction.user_id == user.user_id)
                ).scalars().all()
                
                # Candidates excluding interacted (DB + current session)
                candidates = [c for c in target_coordis 
                              if c.coordi_id not in interacted_coordis_db 
                              and c.coordi_id not in current_user_interacted_ids]
                
                if candidates:
                    num_browsing = random.randint(150, 300)
                    
                    # Split candidates into preferred style and others
                    style_candidates = [c for c in candidates if c.style in preferred_styles]
                    other_candidates = [c for c in candidates if c.style not in preferred_styles]
                    
                    selected_coordis = []
                    
                    # Try to fill 70% with preferred styles
                    target_style_count = int(num_browsing * 0.7)
                    
                    # Use sets to avoid duplicates when merging
                    picked_style_coordis = []
                    if len(style_candidates) >= target_style_count:
                        picked_style_coordis = random.sample(style_candidates, k=target_style_count)
                    else:
                        picked_style_coordis = style_candidates
                    
                    selected_coordis.extend(picked_style_coordis)
                    
                    remaining_count = num_browsing - len(selected_coordis)
                    
                    # Remaining pool: others + (style candidates not picked)
                    remaining_pool = other_candidates + [c for c in style_candidates if c not in picked_style_coordis]
                    
                    if remaining_pool:
                        selected_coordis.extend(random.sample(remaining_pool, k=min(remaining_count, len(remaining_pool))))

                    for coordi in selected_coordis:
                        coordi_id = coordi.coordi_id
                        
                        if coordi_id in current_user_interacted_ids:
                            continue

                        # 10% like, 90% skip
                        action_type = "like" if random.random() < 0.1 else "skip"
                        
                        interaction = UserCoordiInteraction(
                            user_id=user.user_id,
                            coordi_id=coordi_id,
                            action_type=action_type
                        )
                        db.add(interaction)
                        interaction_count += 1
                        current_user_interacted_ids.add(coordi_id)

                        # Create View Log
                        duration = random.randint(5, 30) if action_type == "like" else random.randint(1, 5)
                        view_log = UserCoordiViewLog(
                            user_id=user.user_id,
                            coordi_id=coordi_id,
                            duration_seconds=duration,
                            view_started_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))
                        )
                        db.add(view_log)
                        view_log_count += 1

                        # Item Saving (if like)
                        if action_type == "like":
                            # Get items for this coordi
                            coordi_items = db.execute(
                                select(CoordiItem.item_id).where(CoordiItem.coordi_id == coordi_id)
                            ).scalars().all()
                            
                            if coordi_items:
                                # Save 1-3 items
                                num_save = random.randint(1, min(3, len(coordi_items)))
                                items_to_save = random.sample(coordi_items, k=num_save)
                                
                                for item_id in items_to_save:
                                    # Check if already saved (DB + current session)
                                    is_saved_db = db.execute(
                                        select(UserClosetItem).where(
                                            UserClosetItem.user_id == user.user_id,
                                            UserClosetItem.item_id == item_id
                                        )
                                    ).scalar_one_or_none()
                                    
                                    if not is_saved_db and item_id not in current_user_saved_item_ids:
                                        closet_item = UserClosetItem(user_id=user.user_id, item_id=item_id)
                                        db.add(closet_item)
                                        saved_item_count += 1
                                        current_user_saved_item_ids.add(item_id)
            
            # Commit periodically
            if user.user_id % 10 == 0:
                db.commit()
                print(f"Processed {user.user_id} users...")

        db.commit()
        print("Data seeding completed successfully!")
        print(f"Total Tags Created: {tag_count}")
        print(f"Total Interactions Created: {interaction_count}")
        print(f"Total View Logs Created: {view_log_count}")
        print(f"Total Saved Items: {saved_item_count}")

    except Exception as e:
        import traceback
        print(f"An error occurred: {e}")
        print(traceback.format_exc())
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
