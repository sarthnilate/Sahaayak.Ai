from typing import List, Tuple


class PrioritizationService:
    @staticmethod
    def calculate_priority(
        category: str,
        water_depth_cm: int | None,
        affected_infrastructure: List[str],
        casualties_flag: bool,
        linked_report_count: int,
        conflicting_evidence: bool = False,
    ) -> Tuple[str, str]:
        """
        Calculates suggested priority (critical, high, medium, low) and human-readable rationale.
        """
        score = 0
        factors = []

        if casualties_flag:
            score += 50
            factors.append("Human distress / potential casualties reported")

        if water_depth_cm and water_depth_cm >= 75:
            score += 35
            factors.append(f"Severe inundation depth ({water_depth_cm}cm >= 75cm threshold)")
        elif water_depth_cm and water_depth_cm >= 40:
            score += 20
            factors.append(f"Moderate waterlogging ({water_depth_cm}cm)")

        critical_infra_keywords = [
            "hospital",
            "railway",
            "station",
            "subway",
            "flyover",
            "highway",
            "power",
            "grid",
            "ambulance",
        ]
        infra_matches = [
            item
            for item in affected_infrastructure
            if any(k in item.lower() for k in critical_infra_keywords)
        ]
        if infra_matches:
            score += 30
            factors.append(f"Critical infrastructure impacted: {', '.join(infra_matches[:2])}")

        if linked_report_count >= 3:
            score += 15
            factors.append(
                f"High community corroboration ({linked_report_count} clustered reports)"
            )

        if conflicting_evidence:
            factors.append("Conflicting claims detected - flagged for urgent ground verification")

        if score >= 60:
            priority = "critical"
        elif score >= 35:
            priority = "high"
        elif score >= 15:
            priority = "medium"
        else:
            priority = "low"

        rationale = " ; ".join(factors) if factors else "Standard localized hazard assessment"
        return priority, f"Priority score {score}: {rationale}"


prioritization_service = PrioritizationService()
