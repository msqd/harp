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
  shape?: "rect" | "db"
}) {
  return (
    <g transform={`translate(${x}, ${y})`}>
      {
        {
          rect: (
            <rect
              width={16}
              height={8 * (h + 1)}
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
              strokeWidth={2}
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
const clientsYOffset = 76
const portsXOffset = 210
const portsYOffset = 100
const remotesXOffset = 410
const remotesYOffset = 100

export function SystemTopologyTabPanel() {
  return (
    <Tab.Panel>
      <Pane>
        <H2>Topology</H2>
        <svg height="400px" width="800px">
          <g>
            <rect
              x={210 - 24}
              y={100 - 8 - 32}
              width={200}
              height={32 + 40 * 3.5 + 12}
              fill={theme`colors.slate.50`}
              stroke={theme`colors.slate.200`}
              strokeWidth={2}
              strokeDasharray="4 4"
            />
            <text x={210 - 2 - 8} y={100 - 16} fontSize={12} fontWeight={600} fill={theme`colors.slate.400`}>
              HARP (proxy)
            </text>

            {data.clients.map((client, i) => (
              <Fragment key={`client-${i}`}>
                <Node x={clientsXOffset} y={clientsYOffset + i * 48} h={2} name={client.name} />
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
