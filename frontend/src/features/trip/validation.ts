import Ajv, { type ValidateFunction } from "ajv";
import addFormats from "ajv-formats";
import schema from "../../../../contracts/trip.schema.json";
import type { Location, LocationSearchResult, PlanResult, PlanningProblem } from "./contracts.generated";

const ajv = new Ajv({ allErrors: true, strict: true });
addFormats(ajv);
ajv.addSchema(schema);

function validator<T>(name: string): ValidateFunction<T> {
  const guard = ajv.getSchema<T>(`${schema.$id}#/definitions/${name}`);
  if (!guard) throw new Error(`Missing generated contract: ${name}`);
  return guard;
}

export const isLocation = validator<Location>("Location");
const isSearchResult = validator<LocationSearchResult>("LocationSearchResult");
const isPlanResult = validator<PlanResult>("PlanResult");
export const isPlanningProblem = validator<PlanningProblem>("PlanningProblem");

export function parsePlanResult(value: unknown): PlanResult {
  if (!isPlanResult(value)) throw new Error("The planner returned an invalid response. Please retry.");
  return value;
}

export function parseLocations(value: unknown): Location[] {
  if (!isSearchResult(value)) throw new Error("Address search returned an invalid response. Please retry.");
  return value.locations;
}
