import { BarChart, LineChart } from "echarts/charts"
import {
  DatasetComponent,
  GridComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components"
import * as echarts from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import ReactEChartsCore from "echarts-for-react/lib/core"

import { getTpdexRating, tpdexScale } from "Components/Badges/constants.ts"
import { defaultEchartOptions } from "Settings"

echarts.use([
  LineChart,
  BarChart,
  CanvasRenderer,
  GridComponent,
  TooltipComponent,
  TitleComponent,
  DatasetComponent,
  VisualMapComponent,
])

const tooltipFormatter = (params: { name: string; value: number }[]) => {
  const tpdexSerie = params[0]
  let tooltipContent = `<strong>${tpdexSerie.name}</strong><br/>`
  const rating = getTpdexRating(tpdexSerie.value)
  tooltipContent += `<small>Average TPDEX: ${tpdexSerie.value} (${rating.label})</small>`
  return tooltipContent
}

const tickFormatter = (tick: string) => {
  const date = new Date(tick)
  return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
}

const SummaryPerformancesChart = ({ data }: { data: { value: number; datetime: string }[] }) => {
  const echartOptions = {
    ...defaultEchartOptions,
    grid: {
      ...defaultEchartOptions.grid,
      left: 4,
      right: 64,
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
        type: "line",
        smooth: true,
        symbol: "none",
        lineStyle: {
          width: 4,
        },
      },
    ],
    visualMap: {
      bottom: 4,
      right: 4,
      pieces: [...Array(tpdexScale.length - 1).keys()].map((i) =>
        i
          ? {
              label: tpdexScale[i].label,
              lt: tpdexScale[i - 1].threshold,
              gte: tpdexScale[i].threshold,
              color: tpdexScale[i].bgColor,
            }
          : {
              label: tpdexScale[i].label,
              gte: tpdexScale[i].threshold,
              color: tpdexScale[i].bgColor,
            },
      ),
      outOfRange: {
        color: "#999",
      },
    },
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

export default SummaryPerformancesChart
