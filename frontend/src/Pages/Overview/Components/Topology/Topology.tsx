import { KeyValueSettings } from "Domain/System/useSystemSettingsQuery"
import { H2 } from "mkui/Components/Typography"

type endpoint = {
  name: string
  port: number
  url: string
  description?: string
}

type ProxySettings = {
  endpoints: endpoint[]
}

type Settings = {
  proxy: ProxySettings
  // include other properties of settings here if needed
}

export const Topology = ({
  settings,
  className,
  title,
}: {
  settings?: Settings
  className?: string
  title?: string
}) => {
  //   const endpoints = settings.proxy.endpoints

  const endpoints = [
    { name: "foo", port: 4000, url: "http://localhost:3000" },
    { name: "bar", port: 3000, url: "http://localhost:3000" },
    { name: "baz", port: 2000, url: "http://localhost:3000" },
  ]
  return (
    <div className={className}>
      <H2 className="p-2">{title}</H2>
      <div className="items-center jutify-center self-center">
        <svg className="container" viewBox={`0 0 650 ${50 + 100 * endpoints.length}`}>
          <defs>
            <marker
              id="arrow"
              markerWidth="10"
              markerHeight="10"
              refX="0"
              refY="3"
              orient="auto"
              markerUnits="strokeWidth"
            >
              <path d="M0,0 L0,6 L9,3 z" fill="#000" />
            </marker>
          </defs>
          <rect x="50" y={50 + (100 * (endpoints.length - 1)) / 2} width="100" height="50" fill="lightblue" />
          <text
            x="95"
            y={75 + (100 * (endpoints.length - 1)) / 2}
            fill="black"
            textAnchor="middle"
            dominantBaseline="middle"
          >
            Localhost
          </text>

          <rect x="250" y="50" width="150" height={70 + 100 * (endpoints.length - 1)} fill="lightblue" />
          <text x="300" y={75 + (100 * (endpoints.length - 1)) / 2} fill="black">
            HARP
          </text>

          <line
            x1="150"
            y1={75 + (100 * (endpoints.length - 1)) / 2}
            x2="240"
            y2={75 + (100 * (endpoints.length - 1)) / 2}
            stroke="black"
            markerEnd="url(#arrow)"
          />

          {endpoints.map((endpoint, index) => (
            <g key={index}>
              <rect x="500" y={60 + index * 100} width="100" height="50" fill="lightblue" />
              <text x="535" y={90 + index * 100} fill="black">
                {endpoint.name}
              </text>
              <line
                x1="400"
                y1={85 + index * 100}
                x2="490"
                y2={85 + index * 100}
                stroke="black"
                markerEnd="url(#arrow)"
              />
            </g>
          ))}
        </svg>
      </div>
    </div>
  )
}
