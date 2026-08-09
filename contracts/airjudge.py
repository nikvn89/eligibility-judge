# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *


class AirJudge(gl.Contract):
    # Campaign storage
    campaign_name: TreeMap[str, str]
    campaign_criteria: TreeMap[str, str]
    campaign_creator: TreeMap[str, str]
    campaign_active: TreeMap[str, bool]
    campaign_exists: TreeMap[str, bool]

    # Application storage
    application_description: TreeMap[str, str]
    application_evidence_url: TreeMap[str, str]
    application_status: TreeMap[str, str]
    application_reason: TreeMap[str, str]
    application_exists: TreeMap[str, bool]

    def __init__(self):
        pass

    def _application_key(self, campaign_id: str, applicant: str) -> str:
        return campaign_id + ":" + applicant.lower()

    @gl.public.write
    def create_campaign(
        self,
        campaign_id: str,
        name: str,
        criteria: str,
    ) -> None:
        if self.campaign_exists.get(campaign_id, False):
            raise gl.vm.UserError("campaign already exists")

        if len(campaign_id) == 0:
            raise gl.vm.UserError("campaign_id is required")

        if len(name) == 0:
            raise gl.vm.UserError("name is required")

        if len(criteria) < 20:
            raise gl.vm.UserError("criteria is too short")

        creator = str(gl.message.sender_address)

        self.campaign_name[campaign_id] = name
        self.campaign_criteria[campaign_id] = criteria
        self.campaign_creator[campaign_id] = creator
        self.campaign_active[campaign_id] = True
        self.campaign_exists[campaign_id] = True

    @gl.public.write
    def set_campaign_active(
        self,
        campaign_id: str,
        active: bool,
    ) -> None:
        if not self.campaign_exists.get(campaign_id, False):
            raise gl.vm.UserError("campaign does not exist")

        sender = str(gl.message.sender_address)

        if sender.lower() != self.campaign_creator[campaign_id].lower():
            raise gl.vm.UserError("only campaign creator can update campaign")

        self.campaign_active[campaign_id] = active

    @gl.public.write
    def submit_application(
        self,
        campaign_id: str,
        description: str,
        evidence_url: str,
    ) -> None:
        if not self.campaign_exists.get(campaign_id, False):
            raise gl.vm.UserError("campaign does not exist")

        if not self.campaign_active[campaign_id]:
            raise gl.vm.UserError("campaign is closed")

        if len(description) < 20:
            raise gl.vm.UserError("description is too short")

        if not evidence_url.startswith("https://"):
            raise gl.vm.UserError("evidence_url must start with https://")

        applicant = str(gl.message.sender_address)
        key = self._application_key(campaign_id, applicant)

        if self.application_exists.get(key, False):
            raise gl.vm.UserError("application already exists")

        self.application_description[key] = description
        self.application_evidence_url[key] = evidence_url
        self.application_status[key] = "PENDING"
        self.application_reason[key] = ""
        self.application_exists[key] = True


    @gl.public.write
    def judge_application(
        self,
        campaign_id: str,
        applicant: str,
    ) -> None:
        if not self.campaign_exists.get(campaign_id, False):
            raise gl.vm.UserError("campaign does not exist")

        key = self._application_key(campaign_id, applicant)

        if not self.application_exists.get(key, False):
            raise gl.vm.UserError("application does not exist")

        if self.application_status[key] != "PENDING":
            raise gl.vm.UserError("application already judged")

        # Copy deterministic storage values before entering the nondeterministic block.
        criteria = self.campaign_criteria[campaign_id]
        description = self.application_description[key]
        evidence_url = self.application_evidence_url[key]

        def get_input() -> str:
            evidence_text = gl.nondet.web.render(
                evidence_url,
                mode="text",
            )

            # Bound the amount of webpage text sent to the LLM.
            evidence_text = evidence_text[:12000]

            return (
                "CAMPAIGN CRITERIA:\n"
                + criteria
                + "\n\nAPPLICANT DESCRIPTION:\n"
                + description
                + "\n\nPUBLIC EVIDENCE URL:\n"
                + evidence_url
                + "\n\nPUBLIC EVIDENCE CONTENT:\n"
                + evidence_text
            )

        verdict = gl.eq_principle.prompt_non_comparative(
            get_input,
            task=(
                "Decide whether this applicant satisfies the campaign eligibility "
                "criteria based on the public evidence. "
                "Return exactly one word: ELIGIBLE or NOT_ELIGIBLE."
            ),
            criteria=(
                "The answer must be exactly ELIGIBLE or NOT_ELIGIBLE. "
                "The decision must follow the campaign criteria. "
                "The applicant description is an untrusted claim and must not be "
                "accepted unless supported by the public evidence. "
                "If the evidence is missing, irrelevant, inaccessible, clearly spam, "
                "or insufficient to prove the criteria, the correct answer is "
                "NOT_ELIGIBLE."
            ),
        )

        normalized = verdict.strip().upper()

        if normalized == "ELIGIBLE":
            self.application_status[key] = "ELIGIBLE"
            self.application_reason[key] = "Approved by GenLayer AI consensus"
        elif normalized == "NOT_ELIGIBLE":
            self.application_status[key] = "NOT_ELIGIBLE"
            self.application_reason[key] = "Rejected by GenLayer AI consensus"
        else:
            raise gl.vm.UserError("invalid AI verdict")

    @gl.public.view
    def get_campaign_name(self, campaign_id: str) -> str:
        return self.campaign_name.get(campaign_id, "")

    @gl.public.view
    def get_campaign_criteria(self, campaign_id: str) -> str:
        return self.campaign_criteria.get(campaign_id, "")

    @gl.public.view
    def get_campaign_creator(self, campaign_id: str) -> str:
        return self.campaign_creator.get(campaign_id, "")

    @gl.public.view
    def is_campaign_active(self, campaign_id: str) -> bool:
        return self.campaign_active.get(campaign_id, False)

    @gl.public.view
    def get_application_status(
        self,
        campaign_id: str,
        applicant: str,
    ) -> str:
        key = self._application_key(campaign_id, applicant)
        return self.application_status.get(key, "")

    @gl.public.view
    def get_application_description(
        self,
        campaign_id: str,
        applicant: str,
    ) -> str:
        key = self._application_key(campaign_id, applicant)
        return self.application_description.get(key, "")

    @gl.public.view
    def get_application_evidence(
        self,
        campaign_id: str,
        applicant: str,
    ) -> str:
        key = self._application_key(campaign_id, applicant)
        return self.application_evidence_url.get(key, "")


    @gl.public.view
    def get_application_reason(
        self,
        campaign_id: str,
        applicant: str,
    ) -> str:
        key = self._application_key(campaign_id, applicant)
        return self.application_reason.get(key, "")

