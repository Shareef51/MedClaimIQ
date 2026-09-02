from app.domain.regulatory_control_testing import regulatory_control_testing_contract
from app.services.regulatory_control_testing import RegulatoryControlTestingService

def main():
    c=regulatory_control_testing_contract();assert c['authority']['human_independent_conclusion_required'];assert not c['authority']['ai_can_certify_controls']
    s=RegulatoryControlTestingService.select_risk_based_sample([{'key':'low','risk_score':5},{'key':'high','risk_score':95}],1)
    assert s[0]['key']=='high'
    print('Release 57 regulatory control testing verification: PASS')
if __name__=='__main__':main()
