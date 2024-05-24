type endpoint = {
  name: string
  port: number
  url: string
  description?: string
}

type Endpoints = endpoint[]

export const Topology = ({ endpoints }: { endpoints?: Endpoints }) => {
  return (
    endpoints && (
      <svg className="container" viewBox={`0 0 700 ${50 + 100 * endpoints.length}`}>
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
          x="100"
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

        {endpoints.map((endpoint, index) => {
          const padding = 20 // Adjust this value as needed
          const strLength = endpoint.name.length * 8
          const width = padding + strLength
          const rectX = 500
          const textX = rectX + width / 2
          return (
            <g key={index}>
              <rect x="500" y={60 + index * 100} width={width} height="50" fill="lightblue" />
              <text x={textX} y={90 + index * 100} fill="black" textAnchor="middle" dominantBaseline="middle">
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
          )
        })}
      </svg>
    )
  )
}
