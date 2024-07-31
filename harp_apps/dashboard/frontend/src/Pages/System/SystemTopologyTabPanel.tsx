import { Fragment, useState } from "react"
import { Vector2 } from "three"
import { theme } from "twin.macro"

import { Pane } from "ui/Components/Pane"
import { Tab } from "ui/Components/Tabs"
import { H2 } from "ui/Components/Typography"

function Node({
  x,
  y,
  h = 1,
  labelOffsetX = 0,
  labelOffsetY = 0,
  name,
  shape = "rect",
}: {
  x: number
  y: number
  labelOffsetX?: number
  labelOffsetY?: number
  h?: number
  name: string
  shape?: "rect" | "db" | "globe"
}) {
  return (
    <g transform={`translate(${x}, ${y + 4 * (h - 1)})`}>
      {
        {
          rect: (
            <rect
              width={16}
              height={16}
              rx={2}
              ry={2}
              fill={theme`colors.slate.100`}
              strokeWidth={2}
              stroke={theme`colors.slate.600`}
            />
          ),
          db: (
            <path
              d="m14.7,3.36c0,1.84 -3,3.34 -6.7,3.34s-6.7,-1.5 -6.7,-3.34m13.4,0c0,-1.86 -3,-3.36 -6.7,-3.36s-6.7,1.5 -6.7,3.36m13.4,0l0,9.14c0,1.84 -3,3.34 -6.7,3.34s-6.7,-1.5 -6.7,-3.34l0,-9.14m13.4,0l0,3.05m-13.4,-3.05l0,3.05m13.4,0l0,3.05c0,1.84 -3,3.34 -6.7,3.34s-6.7,-1.5 -6.7,-3.34l0,-3.05m13.4,0c0,1.84 -3,3.34 -6.7,3.34s-6.7,-1.5 -6.7,-3.34"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill={theme`colors.slate.100`}
              strokeWidth={1.5}
              stroke={theme`colors.slate.600`}
            />
          ),
          globe: (
            <path
              d="m7.85,15.7a7.85,7.85 0 0 0 7.61,-5.89m-7.61,5.89a7.85,7.85 0 0 1 -7.61,-5.89m7.61,5.89c2.16,0 3.93,-3.52 3.93,-7.85s-1.76,-7.85 -3.93,-7.85m0,15.7c-2.16,0 -3.93,-3.52 -3.93,-7.85s1.76,-7.85 3.93,-7.85m0,0a7.85,7.85 0 0 1 6.84,3.99m-6.84,-3.99a7.85,7.85 0 0 0 -6.84,3.99m13.68,0a10.42,10.42 0 0 1 -6.84,2.55c-2.62,0 -5.01,-0.96 -6.84,-2.55m13.68,0a7.82,7.82 0 0 1 1.01,3.86c0,0.68 -0.09,1.33 -0.24,1.96m0,0a15.63,15.63 0 0 1 -7.61,1.96c-2.76,0 -5.35,-0.71 -7.61,-1.96m0,0a7.87,7.87 0 0 1 -0.24,-1.96c0,-1.4 0.37,-2.71 1.01,-3.86"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill={theme`colors.slate.100`}
              strokeWidth={1.5}
              stroke={theme`colors.slate.600`}
            />
          ),
        }[shape]
      }
      <text x={labelOffsetX} y={labelOffsetY + 8 * (h + 1) + 12} fontSize={10}>
        {name}
      </text>
    </g>
  )
}

const vOrigin = new Vector2(0, 0)
const vArrow = new Vector2(-10, -3)
const yGap = 2
const xGap = 3

function Link({ x1, y1, x2, y2 }: { x1: number; y1: number; x2: number; y2: number }) {
  const [hover, setHover] = useState<boolean>(false)

  const vFrom = new Vector2(x1, y1)
  const vTo = new Vector2(x2, y2)
  const vAngle = vTo.clone().sub(vFrom).angle()
  const vOppAngle = (vAngle + Math.PI) % (2 * Math.PI)

  const vBackgroundFrom = vFrom.clone().add(new Vector2(xGap, 0).rotateAround(vOrigin, vAngle))
  const vBackgroundTo = vTo.clone().add(new Vector2(-xGap, 0).rotateAround(vOrigin, vAngle))

  const vInFrom = vFrom.clone().add(new Vector2(xGap, -yGap).rotateAround(vOrigin, vAngle))
  const vInTo = vTo.clone().add(new Vector2(-xGap, -yGap).rotateAround(vOrigin, vAngle))
  const vInArrow = vArrow.clone().rotateAround(vOrigin, vAngle).add(vInTo)

  const vOutFrom = vTo.clone().add(new Vector2(xGap, -yGap).rotateAround(vOrigin, vOppAngle))
  const vOutTo = vFrom.clone().add(new Vector2(-xGap, -yGap).rotateAround(vOrigin, vOppAngle))
  const vOutArrow = vArrow.clone().rotateAround(vOrigin, vOppAngle).add(vOutTo)

  return (
    <g onMouseOver={() => setHover(true)} onMouseOut={() => setHover(false)}>
      <path
        d={`M${vBackgroundFrom.x},${vBackgroundFrom.y} L${vBackgroundTo.x},${vBackgroundTo.y}`}
        stroke="white"
        strokeWidth={6 + yGap - 1}
      />

      <path
        d={`M${vInFrom.x},${vInFrom.y} L${vInTo.x},${vInTo.y} L${vInArrow.x},${vInArrow.y}`}
        fill="none"
        stroke={theme`colors.cyan.300`}
        strokeWidth={3}
        style={hover ? { filter: "saturate(.5)", zIndex: 10 } : { filter: "saturate(.2)" }}
      />
      <path
        d={`M${vOutFrom.x},${vOutFrom.y} L${vOutTo.x},${vOutTo.y} L${vOutArrow.x},${vOutArrow.y}`}
        fill="none"
        stroke={theme`colors.lime.300`}
        strokeWidth={3}
        style={hover ? { filter: "saturate(.5)" } : { filter: "saturate(.2)" }}
      />
    </g>
  )
}

const data = {
  clients: [{ name: "default" }, { name: "dmz" }, { name: "internal" }, { name: "contractors" }],
  ports: [
    { name: "httpbin-1", port: 4000 },
    { name: "httpbin-2", port: 4001 },
  ],
  remotes: [{ name: "httpbin-1" }, { name: "httpbin-2" }],
}

const clientsXOffset = 10
const clientsYOffset = 24
const portsXOffset = 210
const portsYOffset = 48
const remotesXOffset = 410
const remotesYOffset = 48

export function SystemTopologyTabPanel() {
  return (
    <Tab.Panel>
      <Pane>
        <H2>Topology</H2>
        <svg height="400px" width="800px">
          <g>
            <rect
              x={portsXOffset - 24}
              y={remotesYOffset - 40}
              width={200}
              height={32 + 40 * 4.5 + 24}
              fill={theme`colors.slate.50`}
              stroke={theme`colors.slate.200`}
              strokeWidth={2}
              strokeDasharray="4 4"
            />
            <text
              x={portsXOffset - 2 - 8}
              y={portsYOffset - 16}
              fontSize={12}
              fontWeight={600}
              fill={theme`colors.slate.400`}
            >
              HARP (proxy)
            </text>

            {data.clients.map((client, i) => (
              <Fragment key={`client-${i}`}>
                <Node x={clientsXOffset} y={clientsYOffset + i * 48} h={2} name={client.name} shape="globe" />
                <Link x1={clientsXOffset + 16} y1={clientsYOffset + i * 48 + 8} x2={210} y2={100 + 8} />
                <Link x1={clientsXOffset + 16} y1={clientsYOffset + i * 48 + 8 + 8} x2={210} y2={140 + 8} />
              </Fragment>
            ))}

            {data.ports.map((port, i) => (
              <Fragment key={`port-${i}`}>
                <Link x1={portsXOffset + 8} y1={portsYOffset + i * 40 + 16} x2={portsXOffset + 8} y2={200} />
                <Node x={portsXOffset} y={portsYOffset + i * 40} labelOffsetX={16} name={port.name} />
              </Fragment>
            ))}

            <Node x={210} y={200} name="Cache" shape="db" />

            {data.remotes.map((remote, i) => (
              <Fragment key={`remote-${i}`}>
                <Link
                  x1={portsXOffset + 16}
                  y1={portsYOffset + 8 + i * 40}
                  x2={remotesXOffset}
                  y2={remotesYOffset + 8 + i * 40}
                />
                <Node x={remotesXOffset} y={remotesYOffset + i * 40} name={`${remote.name} (remote)`} />
              </Fragment>
            ))}
          </g>
        </svg>
      </Pane>
    </Tab.Panel>
  )
}
