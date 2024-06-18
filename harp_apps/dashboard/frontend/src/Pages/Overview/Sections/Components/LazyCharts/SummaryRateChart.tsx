import { BarChart, LineChart } from "echarts/charts"
import { DatasetComponent, GridComponent, TitleComponent, TooltipComponent } from "echarts/components"
import * as echarts from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import ReactEChartsCore from "echarts-for-react/lib/core"

import { defaultEchartOptions } from "Settings"

echarts.use([LineChart, BarChart, CanvasRenderer, GridComponent, TooltipComponent, TitleComponent, DatasetComponent])

const tooltipFormatter = (params: { name: string; value: number }[]) => {
  const serie = params[0]
  let tooltipContent = `<strong>${serie.name}</strong><br/>`
  tooltipContent += `<small>Errors: ${serie.value}</small>`
  return tooltipContent
}

const tickFormatter = (tick: string) => {
  const date = new Date(tick)
  return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
}

const SummaryRateChart = ({
  data,
  color = undefined,
}: {
  data: { value: number; datetime: string }[]
  color?: string
}) => {
  const echartOptions = {
    ...defaultEchartOptions,
    grid: {
      ...defaultEchartOptions.grid,
      left: 8,
      right: 8,
      top: 64,
      bottom: 24,
    },
    xAxis: {
      type: "category",
      data: data.map((x) => tickFormatter(x.datetime)),
    },
    yAxis: {
      axisLabel: { show: false },
    },
    tooltip: {
      ...defaultEchartOptions.tooltip,
      formatter: tooltipFormatter,
    },
    series: [
      {
        data: data.map((x) => x.value),
        type: "bar",
        smooth: false,
        symbol: "none",
        lineStyle: {
          width: 4,
        },
        color: color,
      },
    ],
  }
  return (
    <ReactEChartsCore
      echarts={echarts}
      option={echartOptions}
      notMerge={true}
      lazyUpdate={true}
      opts={{ height: 240, width: "auto" }}
    />
  )
}

export default SummaryRateChart
