import { BarChart, LineChart } from "echarts/charts"
import { DatasetComponent, GridComponent, TitleComponent, TooltipComponent } from "echarts/components"
import * as echarts from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import ReactEChartsCore from "echarts-for-react/lib/core"
import { useMemo } from "react"

import { OverviewTransaction } from "Models/Overview"
import { defaultEchartOptions } from "Settings"

echarts.use([LineChart, BarChart, CanvasRenderer, GridComponent, TooltipComponent, TitleComponent, DatasetComponent])

interface TransactionsChartProps {
  data: Array<OverviewTransaction>
  timeRange?: string
}
const labelOption = {
  show: true,
  rotate: 90,
  formatter: "{c}",
  fontSize: 12,
  color: "#065f9f",
  rich: {
    name: {},
  },
}

const tooltipFormatter = function (params: { name: string; value: number }[]) {
  const countSerie = params[0]
  let tooltipContent = `<strong>${countSerie.name}</strong><br/>`
  const errorsSerie = params[1]
  const errorRate = countSerie.value
    ? (errorsSerie.value / countSerie.value).toLocaleString(undefined, {
        style: "percent",
        minimumFractionDigits: 1,
      })
    : "n/a"

  const cachedSerie = params[2]
  const cachedRate = countSerie.value
    ? (cachedSerie.value / countSerie.value).toLocaleString(undefined, {
        style: "percent",
        minimumFractionDigits: 1,
      })
    : "n/a"
  if (countSerie.value) {
    tooltipContent += `<small>Transactions: ${countSerie.value}<br/>`
    tooltipContent += `Cached: ${cachedSerie.value} (${cachedRate})<br/>`
    tooltipContent += `Errors: ${errorsSerie.value} (${errorRate})<br/>`
    tooltipContent += "</small>"
  } else {
    tooltipContent += `<small>No transactions</small>`
  }
  return tooltipContent
}

const TransactionsChart = ({ data, timeRange }: TransactionsChartProps) => {
  const echartOptions = useMemo(() => {
    const tickFormatter = (tick: string) => {
      const date = new Date(tick)
      switch (timeRange) {
        case "1h":
          // If time range is 1 hour, return time in 'mm:ss' format
          return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
        case "24h":
          // If time range is 24 hours, return time in 'HH:mm' format
          return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
        case "7d":
          // If time range is 7 days, return short weekday, month, and day
          return date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })
        case "1m":
          // If time range is 1 month, return short month and day
          return date.toLocaleDateString(undefined, { month: "short", day: "numeric" })
        case "1y":
          // If time range is 1 year, return month and full year
          return date.toLocaleDateString(undefined, { month: "short", year: "numeric" })
        default:
          // By default return full date
          return date.toLocaleDateString()
      }
    }
    return {
      ...defaultEchartOptions,
      xAxis: {
        type: "category",
        data: data.map((x) => tickFormatter(x.datetime)),
      },
      yAxis: {
        type: "value",
      },
      tooltip: {
        ...defaultEchartOptions.tooltip,
        formatter: tooltipFormatter,
      },
      series: [
        {
          name: "transactions",
          data: data.map((x) => x.count),
          type: "bar",
          color: "#ADD8E6",
          barWidth: "30px",
          label: labelOption,
        },
        {
          name: "errors",
          data: data.map((x) => x.errors),
          type: "bar",
          barWidth: "10px",
          barGap: "0",
          color: "#e6adad",
          stack: "details",
        },
        {
          name: "cached",
          data: data.map((x) => x.cached),
          type: "bar",
          barWidth: "10px",
          barGap: "0",
          color: "#b9e6ad",
          stack: "details",
        },
        {
          name: "rest",
          data: data.map((x) => x.count - x.errors - x.cached),
          type: "bar",
          barWidth: "10px",
          barGap: "0",
          color: "#e5e5e5",
          stack: "details",
        },
      ],
    }
  }, [data, timeRange])

  return (
    <ReactEChartsCore
      echarts={echarts}
      option={echartOptions}
      notMerge={true}
      lazyUpdate={true}
      opts={{ height: 300, width: "auto" }}
    />
  )
}

export default TransactionsChart
