import { apiClient } from "@/services/api/client";
import { ComplianceDigitalTwin, DigitalTwinSnapshot } from "@/types/api";

export async function getComplianceDigitalTwin() {
  const { data } = await apiClient.get<ComplianceDigitalTwin>("/digital-twin");
  if (process.env.NODE_ENV === "development") {
    console.log("Twin API Response", data);
  }
  return data;
}

export async function rebuildComplianceDigitalTwin() {
  const { data } = await apiClient.post<ComplianceDigitalTwin>("/digital-twin/rebuild");
  if (process.env.NODE_ENV === "development") {
    console.log("Twin API Response", data);
  }
  return data;
}

export async function getComplianceDigitalTwinHistory() {
  const { data } = await apiClient.get<DigitalTwinSnapshot[]>("/digital-twin/history");
  return data;
}
