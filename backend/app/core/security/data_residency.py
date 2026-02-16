"""
Data Residency and Geo-fencing
Enterprise data location control and compliance
"""
import os
import json
import logging
from typing import Optional, Dict, List, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import geoip2.database
import geoip2.errors

logger = logging.getLogger(__name__)


class DataClassification(Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    REGULATED = "regulated"


class RegionCode(Enum):
    """Geographic region codes"""
    US = "US"                    # United States
    EU = "EU"                    # European Union
    UK = "UK"                    # United Kingdom
    CA = "CA"                    # Canada
    AU = "AU"                    # Australia
    JP = "JP"                    # Japan
    SG = "SG"                    # Singapore
    IN = "IN"                    # India
    BR = "BR"                    # Brazil
    GLOBAL = "GLOBAL"            # Global/Any


@dataclass
class GeoLocation:
    """Geographic location"""
    country_code: str
    region_code: str
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    is_in_eu: bool = False


@dataclass
class DataResidencyPolicy:
    """Data residency policy"""
    id: str
    name: str
    data_classification: DataClassification
    allowed_regions: List[RegionCode]
    primary_region: RegionCode
    replication_regions: List[RegionCode] = field(default_factory=list)
    encryption_required: bool = True
    cross_border_transfer_allowed: bool = False
    audit_logging_required: bool = True
    retention_days: int = 2555  # 7 years default
    legal_hold_capable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataResidencyRule:
    """Data residency rule for specific data types"""
    data_type: str
    classification: DataClassification
    allowed_regions: List[RegionCode]
    prohibited_regions: List[RegionCode] = field(default_factory=list)
    requires_consent: bool = False
    consent_mechanism: Optional[str] = None


class GeoIPResolver:
    """Resolves IP addresses to geographic locations"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.environ.get('GEOIP_DB_PATH', '/usr/share/GeoIP/GeoLite2-City.mmdb')
        self._reader = None
        self._load_database()
    
    def _load_database(self):
        """Load GeoIP database"""
        try:
            if os.path.exists(self.db_path):
                self._reader = geoip2.database.Reader(self.db_path)
                logger.info(f"Loaded GeoIP database: {self.db_path}")
            else:
                logger.warning(f"GeoIP database not found: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to load GeoIP database: {e}")
    
    def resolve_ip(self, ip_address: str) -> Optional[GeoLocation]:
        """Resolve IP address to geographic location"""
        if not self._reader:
            return None
        
        try:
            response = self._reader.city(ip_address)
            
            return GeoLocation(
                country_code=response.country.iso_code,
                region_code=self._get_region_code(response.country.iso_code),
                city=response.city.name,
                latitude=response.location.latitude,
                longitude=response.location.longitude,
                timezone=response.location.time_zone,
                is_in_eu=response.country.is_in_european_union or False
            )
        except geoip2.errors.AddressNotFoundError:
            logger.debug(f"IP address not found in GeoIP database: {ip_address}")
            return None
        except Exception as e:
            logger.error(f"GeoIP resolution failed: {e}")
            return None
    
    def _get_region_code(self, country_code: str) -> str:
        """Map country code to region code"""
        eu_countries = {
            'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR',
            'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL',
            'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE'
        }
        
        if country_code in eu_countries:
            return 'EU'
        
        region_mapping = {
            'US': 'US', 'CA': 'CA', 'MX': 'US',
            'GB': 'UK', 'UK': 'UK',
            'AU': 'AU', 'NZ': 'AU',
            'JP': 'JP', 'KR': 'JP', 'CN': 'JP',
            'SG': 'SG', 'MY': 'SG', 'TH': 'SG',
            'IN': 'IN', 'PK': 'IN',
            'BR': 'BR', 'AR': 'BR', 'CL': 'BR'
        }
        
        return region_mapping.get(country_code, 'GLOBAL')


class DataResidencyManager:
    """Manages data residency policies and enforcement"""
    
    def __init__(self):
        self._policies: Dict[str, DataResidencyPolicy] = {}
        self._rules: Dict[str, DataResidencyRule] = {}
        self._data_locations: Dict[str, GeoLocation] = {}
        self._geo_resolver = GeoIPResolver()
        self._audit_log: List[Dict] = []
    
    def register_policy(self, policy: DataResidencyPolicy):
        """Register a data residency policy"""
        self._policies[policy.id] = policy
        logger.info(f"Registered data residency policy: {policy.name}")
    
    def register_rule(self, rule: DataResidencyRule):
        """Register a data residency rule"""
        self._rules[rule.data_type] = rule
    
    def check_data_access(self, data_id: str, 
                          data_classification: DataClassification,
                          user_location: GeoLocation,
                          action: str = "read") -> Dict:
        """Check if data access complies with residency policy"""
        # Find applicable policy
        policy = self._find_policy(data_classification)
        if not policy:
            return {
                'allowed': True,
                'reason': 'No policy found',
                'policy_id': None
            }
        
        # Check if user region is allowed
        user_region = RegionCode(user_location.region_code)
        
        if user_region not in policy.allowed_regions:
            self._log_access_violation(data_id, user_location, policy, action)
            return {
                'allowed': False,
                'reason': f'Access from {user_region.value} not allowed for this data',
                'policy_id': policy.id,
                'violation_type': 'region_not_allowed'
            }
        
        # Check cross-border transfer
        data_location = self._data_locations.get(data_id)
        if data_location and action in ['read', 'write']:
            if data_location.region_code != user_location.region_code:
                if not policy.cross_border_transfer_allowed:
                    return {
                        'allowed': False,
                        'reason': 'Cross-border data transfer not allowed',
                        'policy_id': policy.id,
                        'violation_type': 'cross_border_transfer'
                    }
        
        return {
            'allowed': True,
            'reason': 'Access complies with residency policy',
            'policy_id': policy.id
        }
    
    def _find_policy(self, classification: DataClassification) -> Optional[DataResidencyPolicy]:
        """Find policy for data classification"""
        for policy in self._policies.values():
            if policy.data_classification == classification:
                return policy
        return None
    
    def _log_access_violation(self, data_id: str, 
                               location: GeoLocation,
                               policy: DataResidencyPolicy,
                               action: str):
        """Log residency policy violation"""
        violation = {
            'timestamp': datetime.utcnow().isoformat(),
            'data_id': data_id,
            'location': {
                'country': location.country_code,
                'region': location.region_code
            },
            'policy_id': policy.id,
            'action': action,
            'type': 'residency_violation'
        }
        
        self._audit_log.append(violation)
        logger.warning(f"Data residency violation: {violation}")
    
    def set_data_location(self, data_id: str, location: GeoLocation):
        """Set geographic location of data"""
        self._data_locations[data_id] = location
    
    def get_data_location(self, data_id: str) -> Optional[GeoLocation]:
        """Get geographic location of data"""
        return self._data_locations.get(data_id)
    
    def resolve_and_set_location(self, data_id: str, ip_address: str):
        """Resolve IP and set data location"""
        location = self._geo_resolver.resolve_ip(ip_address)
        if location:
            self.set_data_location(data_id, location)
        return location


class GDPRComplianceManager:
    """GDPR-specific data residency compliance"""
    
    def __init__(self, residency_manager: DataResidencyManager = None):
        self.residency = residency_manager or DataResidencyManager()
        self._consent_records: Dict[str, Dict] = {}
        self._data_processing_records: List[Dict] = []
    
    def record_consent(self, user_id: str, 
                       consent_type: str,
                       granted: bool,
                       ip_address: str,
                       timestamp: datetime = None):
        """Record user consent for data processing"""
        location = self.residency._geo_resolver.resolve_ip(ip_address)
        
        consent_record = {
            'user_id': user_id,
            'consent_type': consent_type,
            'granted': granted,
            'ip_address': ip_address,
            'location': {
                'country': location.country_code if location else None,
                'is_in_eu': location.is_in_eu if location else None
            },
            'timestamp': (timestamp or datetime.utcnow()).isoformat()
        }
        
        self._consent_records[f"{user_id}:{consent_type}"] = consent_record
        
        logger.info(f"Consent recorded for user {user_id}: {consent_type}={granted}")
    
    def check_gdpr_compliance(self, user_id: str, 
                              data_type: str,
                              processing_purpose: str) -> Dict:
        """Check GDPR compliance for data processing"""
        # Check consent
        consent_key = f"{user_id}:{processing_purpose}"
        consent = self._consent_records.get(consent_key)
        
        if not consent or not consent.get('granted'):
            return {
                'compliant': False,
                'reason': 'Valid consent not obtained',
                'requirement': 'consent'
            }
        
        # Check data location
        rule = self.residency._rules.get(data_type)
        if rule and rule.requires_consent:
            if not consent.get('granted'):
                return {
                    'compliant': False,
                    'reason': 'Explicit consent required for this data type',
                    'requirement': 'explicit_consent'
                }
        
        return {
            'compliant': True,
            'reason': 'GDPR requirements satisfied',
            'consent_record': consent
        }
    
    def generate_processing_record(self, user_id: str,
                                   data_categories: List[str],
                                   processing_purposes: List[str],
                                   retention_period_days: int) -> Dict:
        """Generate GDPR Article 30 processing record"""
        record = {
            'record_id': f"ROPA-{user_id}-{datetime.utcnow().timestamp()}",
            'controller': 'Cerebrum AI Inc.',
            'dpo_contact': 'dpo@cerebrum.ai',
            'purposes': processing_purposes,
            'data_categories': data_categories,
            'recipients': ['internal_systems'],
            'transfers': [],
            'retention_period': f"{retention_period_days} days",
            'security_measures': ['encryption', 'access_control', 'audit_logging'],
            'created_at': datetime.utcnow().isoformat()
        }
        
        self._data_processing_records.append(record)
        return record


class DataTransferController:
    """Controls cross-border data transfers"""
    
    def __init__(self, residency_manager: DataResidencyManager = None):
        self.residency = residency_manager or DataResidencyManager()
        self._transfer_mechanisms: Dict[str, Dict] = {}
        self._transfer_logs: List[Dict] = []
    
    def register_transfer_mechanism(self, mechanism_id: str, 
                                    mechanism_type: str,
                                    config: Dict):
        """Register transfer mechanism (SCCs, BCRs, etc.)"""
        self._transfer_mechanisms[mechanism_id] = {
            'type': mechanism_type,
            'config': config,
            'registered_at': datetime.utcnow().isoformat()
        }
    
    def authorize_transfer(self, data_id: str,
                          from_region: RegionCode,
                          to_region: RegionCode,
                          data_classification: DataClassification) -> Dict:
        """Authorize cross-border data transfer"""
        # Check if transfer is needed
        if from_region == to_region:
            return {
                'authorized': True,
                'mechanism': 'none_required',
                'reason': 'Intra-region transfer'
            }
        
        # Get policy
        policy = None
        for p in self.residency._policies.values():
            if p.data_classification == data_classification:
                policy = p
                break
        
        if not policy:
            return {
                'authorized': False,
                'reason': 'No policy found for data classification'
            }
        
        # Check if cross-border allowed
        if not policy.cross_border_transfer_allowed:
            return {
                'authorized': False,
                'reason': 'Cross-border transfers not allowed for this data'
            }
        
        # Determine transfer mechanism
        mechanism = self._determine_mechanism(from_region, to_region)
        
        # Log transfer
        transfer_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'data_id': data_id,
            'from_region': from_region.value,
            'to_region': to_region.value,
            'mechanism': mechanism,
            'authorized': True
        }
        self._transfer_logs.append(transfer_record)
        
        return {
            'authorized': True,
            'mechanism': mechanism,
            'safeguards': self._get_safeguards(mechanism)
        }
    
    def _determine_mechanism(self, from_region: RegionCode, 
                             to_region: RegionCode) -> str:
        """Determine appropriate transfer mechanism"""
        # EU to US
        if from_region == RegionCode.EU and to_region == RegionCode.US:
            return 'standard_contractual_clauses'
        
        # EU to UK
        if from_region == RegionCode.EU and to_region == RegionCode.UK:
            return 'adequacy_decision'
        
        # Default
        return 'standard_contractual_clauses'
    
    def _get_safeguards(self, mechanism: str) -> List[str]:
        """Get safeguards for transfer mechanism"""
        safeguards = {
            'standard_contractual_clauses': [
                'Data encryption in transit',
                'Purpose limitation',
                'Data subject rights',
                'Audit rights'
            ],
            'adequacy_decision': [
                'Equivalent protection level',
                'No additional safeguards required'
            ],
            'binding_corporate_rules': [
                'Internal data protection policies',
                'Enforceable rights',
                'Liability framework'
            ]
        }
        
        return safeguards.get(mechanism, ['General data protection measures'])


# Global instances
residency_manager = DataResidencyManager()
gdpr_manager = GDPRComplianceManager(residency_manager)
transfer_controller = DataTransferController(residency_manager)