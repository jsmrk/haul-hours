import { Temporal } from "@js-temporal/polyfill";

export type TimeChoice = "reject" | "earlier" | "later";

export function resolveDeparture(localDateTime: string, timezone: string, disambiguation: TimeChoice = "reject"): string {
  const plain = Temporal.PlainDateTime.from(localDateTime);
  const earlier = plain.toZonedDateTime(timezone, { disambiguation: "earlier" });
  const later = plain.toZonedDateTime(timezone, { disambiguation: "later" });
  if (!earlier.toPlainDateTime().equals(plain) || !later.toPlainDateTime().equals(plain)) {
    throw new Error("This local time does not exist because the clocks move forward. Choose another time.");
  }
  if (earlier.epochNanoseconds !== later.epochNanoseconds && disambiguation === "reject") {
    throw new Error("This local time occurs twice. Choose the first or second occurrence below.");
  }
  return (disambiguation === "later" ? later : earlier).toInstant().toString();
}

export function localTimeForInstant(instant: string, timezone: string): string {
  return Temporal.Instant.from(instant).toZonedDateTimeISO(timezone).toPlainDateTime().toString({ smallestUnit: "minute" });
}
