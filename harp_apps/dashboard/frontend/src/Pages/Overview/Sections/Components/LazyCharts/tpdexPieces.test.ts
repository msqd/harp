import { describe, expect, it } from "vitest"

import { tpdexScale } from "Components/Badges/constants.ts"

import { tpdexPieces } from "./tpdexPieces.ts"

const piecesMatching = (score: number) =>
  tpdexPieces().filter((p) => (p.gte === undefined || score >= p.gte) && (p.lt === undefined || score < p.lt))

describe("tpdexPieces", () => {
  it("lists every grade of the scale, G included", () => {
    expect(tpdexPieces().map((p) => p.label)).toEqual(tpdexScale.map((r) => r.label))
  })

  it("colours a G score with the G colour", () => {
    const g = tpdexScale[tpdexScale.length - 1]
    expect(piecesMatching(5)).toEqual([expect.objectContaining({ label: "G", color: g.bgColor })])
  })

  it.each([100, 98, 50, 17, 16, 0])("covers score %i exactly once", (score) => {
    expect(piecesMatching(score)).toHaveLength(1)
  })
})
