from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import IncomingParcel, Customer, PointTransaction, ParcelStatus

@receiver(post_save, sender=IncomingParcel)
def award_points_for_parcel(sender, instance, created, **kwargs):
    """Automatically award points when a parcel is processed"""
    # Only award if status is PROCESSED
    if (instance.points_calculated and 
        not instance.points_awarded and 
        instance.status == ParcelStatus.PROCESSED):
        try:
            customer = Customer.objects.get(user=instance.user)
            
            print(f"🔍 Awarding points for parcel ip{instance.pk}")
            print(f"   Customer: {customer.user.username}")
            print(f"   Points: {instance.points_calculated}")
            
            # Add points to customer
            customer.total_points += instance.points_calculated
            customer.save()
            
            # Create transaction record
            PointTransaction.objects.create(
                customer=customer,
                transaction_type='EARNED',
                points=instance.points_calculated,
                description=f"Recycled parcel ip{instance.pk}",
                related_parcel=instance
            )
            
            # Mark parcel as awarded (use update to avoid recursion)
            IncomingParcel.objects.filter(pk=instance.pk).update(points_awarded=True)
            
            # Send email notification about processed parcel
            send_parcel_processed_email(customer, instance)
            
            # Refresh customer from DB to get updated counts
            customer.refresh_from_db()
            
            # Check if customer should be upgraded to premium
            check_and_upgrade_to_premium(customer)
            
        except Customer.DoesNotExist:
            print(f"❌ Customer not found for user {instance.user}")
            pass

def send_parcel_processed_email(customer, parcel):
    """Send email notification when parcel is processed"""
    subject = f'✅ Parcel {parcel} Processed - {parcel.points_calculated} Points Awarded!'
    
    membership_type = "Premium ⭐" if customer.is_premium else "Basic"
    
    message = f"""
Hi {customer.name},

Great news! Your recycling parcel has been processed.

Parcel ID: {parcel}
Points Awarded: {parcel.points_calculated} points
Membership: {membership_type}
Total Points: {customer.total_points} points

Thank you for recycling with KnightCycle!

View your points: http://127.0.0.1:8000/store/profile/

Best regards,
The KnightCycle Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [customer.email],
            fail_silently=False,
        )
        print(f"   📧 Email sent to {customer.email}")
    except Exception as e:
        print(f"   ❌ Failed to send email: {e}")

def check_and_upgrade_to_premium(customer):
    """Check if customer meets premium requirements and upgrade if eligible"""
    parcel_count = customer.get_parcel_count()
    verified_weight = customer.get_verified_weight()
    
    print(f"\n🔍 Checking premium eligibility for {customer.user.username}")
    print(f"   Current premium status: {customer.is_premium}")
    print(f"   Parcel count: {parcel_count}")
    print(f"   Verified weight: {verified_weight}kg")
    print(f"   Needs 10 parcels OR 25kg")
    
    if customer.is_premium:
        print(f"   ⏭️  Already premium, skipping")
        return  # Already premium
    
    # Check eligibility: 10 parcels OR 25kg
    if parcel_count >= 10 or verified_weight >= 25:
        print(f"   ✅ ELIGIBLE! Upgrading to Premium!")
        
        # Upgrade to premium
        customer.is_premium = True
        customer.save()
        
        # Add bonus points for reaching premium
        PointTransaction.objects.create(
            customer=customer,
            transaction_type='BONUS',
            points=500,
            description="🎉 Premium membership unlocked! Welcome bonus"
        )
        
        # Update total points with bonus
        customer.total_points += 500
        customer.save()
        
        # Send premium upgrade email
        send_premium_upgrade_email(customer, parcel_count, verified_weight)
        
        print(f"✨ {customer.user.username} upgraded to Premium with 500 bonus points!")
    else:
        print(f"   ❌ Not eligible yet. Need {10 - parcel_count} more parcels OR {25 - verified_weight:.1f}kg more weight")

def send_premium_upgrade_email(customer, parcel_count, verified_weight):
    """Send email notification when customer is upgraded to premium"""
    subject = '🎉 Congratulations! You\'re Now a Premium Member!'
    
    # Determine which milestone was reached
    if parcel_count >= 10:
        milestone = f"recycling {parcel_count} parcels"
    else:
        milestone = f"recycling {verified_weight:.1f}kg of plastic"
    
    message = f"""
Hi {customer.name},

🎉 CONGRATULATIONS! 🎉

You've been upgraded to PREMIUM membership by {milestone}!

Premium Benefits:
⭐ 20% bonus points on all future recycling
⭐ 500 bonus points added to your account
⭐ Priority processing
⭐ Exclusive rewards

Your Stats:
• Total Parcels: {parcel_count}
• Total Weight Recycled: {verified_weight:.1f}kg
• Current Points: {customer.total_points} points

Keep recycling and earning those premium rewards!

View your premium profile: http://127.0.0.1:8000/store/profile/

Thank you for helping reduce the impact of 3D printing!

Best regards,
The KnightCycle Team 🌍♻️
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [customer.email],
            fail_silently=False,
        )
        print(f"   📧 Premium upgrade email sent to {customer.email}")
    except Exception as e:
        print(f"   ❌ Failed to send premium email: {e}")