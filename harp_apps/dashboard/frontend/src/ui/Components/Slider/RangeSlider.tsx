import { useEffect, useState } from "react"
import { styled, css } from "twin.macro"

export type Mark = number | { value: number; label: string; className?: string }

interface RangeSliderProps {
  min?: number
  max?: number
  defaultValue?: { min?: number; max?: number }
  value?: { min?: number; max?: number }
  step?: number
  onChange?: (value: { min?: number; max?: number }) => void
  onPointerUp?: (value: { min?: number; max?: number }) => void
  thumbSize?: string
  marks?: Mark[]
}

const trackStyles = () => css`
  appearance: none;
  background: transparent;
  border: transparent;
`

const thumbStyles = ({ thumbSize }: { thumbSize: string }) => css`
  appearance: none;
  pointer-events: all;
  width: ${thumbSize};
  height: ${thumbSize};
  border-radius: 0px;
  border: 0 none;
  background-color: blue;
  cursor: grab;

  &:active {
    cursor: grabbing;
  }
`

const Wrapper = styled.div(
  ({ thumbSize }: { thumbSize: string }) => css`
    position: relative;
    display: flex;
    align-items: center;
    margin: 6px calc(${thumbSize} / 2);
    height: calc(${thumbSize} + 1.6rem);
  `,
)
const InputWrapper = styled.div(
  ({ thumbSize }: { thumbSize: string }) => css`
    width: calc(100% + ${thumbSize});
    position: relative;
    margin: 0 calc(${thumbSize} / -2);
    height: ${thumbSize};
  `,
)

const ControlWrapper = styled.div(
  ({ thumbSize }: { thumbSize: string }) => css`
    width: 100%;
    position: absolute;
    height: ${thumbSize};
  `,
)

const Input = styled.input(
  ({ thumbSize }: { thumbSize: string }) => css`
    position: absolute;
    width: 100%;
    pointer-events: none;
    appearance: none;
    height: 100%;
    opacity: 0;
    z-index: 3;
    padding: 0;

    &:focus::-webkit-slider-runnable-track {
      ${trackStyles()};
    }

    &::-webkit-slider-thumb {
      ${thumbStyles({ thumbSize })};
    }
  `,
)

const Rail = styled.div`
  ${css`
    position: absolute;
    width: 100%;
    top: 50%;
    transform: translateY(-50%);
    height: 6px;
    border-radius: 3px;
    background: lightgrey;
  `}
`

const InnerRail = styled.div`
  ${css`
    position: absolute;
    height: 100%;
    background: blue;
    opacity: 0.5;
  `}
`

const Control = styled.div(
  ({ thumbSize }: { thumbSize: string }) => css`
    width: ${thumbSize};
    height: ${thumbSize};
    border-radius: 50%;
    position: absolute;
    background: blue;
    top: 50%;
    margin-left: calc(${thumbSize} / -2);
    transform: translate3d(0, -50%, 0);
    z-index: 2;
  `,
)

const Mark = styled.div(
  ({ className }: { className?: string }) => css`
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 6px;
    height: 6px;
    border-radius: 50%;
    ${className &&
    css`
      @apply ${className};
    `}
  `,
)

const Label = styled.div(
  ({ className }: { className?: string }) => css`
    position: absolute;
    top: 100%;
    transform: translateX(-50%);
    margin-top: 4px;
    font-size: 10px;
    font-weight: 500;
    white-space: nowrap;
    ${className &&
    css`
      @apply ${className};
    `}
  `,
)

const RangeSlider: React.FC<RangeSliderProps> = ({
  min = 0,
  max = 10,
  defaultValue = undefined,
  value,
  step = 1,
  onChange,
  onPointerUp,
  thumbSize = "16px",
  marks,
}) => {
  const [minValue, setMinValue] = useState(
    value && value.min ? value.min : defaultValue && defaultValue.min ? defaultValue.min : min,
  )
  const [maxValue, setMaxValue] = useState(
    value && value.max ? value.max : defaultValue && defaultValue.max ? defaultValue.max : max,
  )

  useEffect(() => {
    const setValues = (values: { min?: number; max?: number } | undefined) => {
      if (values) {
        values.min !== undefined ? setMinValue(values.min) : setMinValue(min)
        values.max !== undefined ? setMaxValue(values.max) : setMaxValue(max)
      } else {
        setMinValue(min)
        setMaxValue(max)
      }
    }

    if (!defaultValue) {
      setValues(value)
    } else {
      setValues(defaultValue)
    }
  }, [max, min, value, defaultValue])

  const handlePointerUp = () => {
    if (onPointerUp) onPointerUp({ min: minValue, max: maxValue })
  }

  const handleMinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    const newMinVal = Math.min(Number(e.target.value), maxValue - step)
    if (!value) setMinValue(newMinVal)
    if (onChange) onChange({ min: newMinVal, max: maxValue })
  }

  const handleMaxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    const newMaxVal = Math.max(Number(e.target.value), minValue + step)
    if (!value) setMaxValue(newMaxVal)
    if (onChange) onChange({ min: minValue, max: newMaxVal })
  }
  const minPos = ((minValue - min) / (max - min)) * 100
  const maxPos = ((maxValue - min) / (max - min)) * 100

  return (
    <Wrapper thumbSize={thumbSize}>
      <InputWrapper thumbSize={thumbSize}>
        <Input
          className="input"
          type="range"
          value={minValue}
          min={min}
          max={max}
          step={step}
          onChange={handleMinChange}
          onPointerUp={handlePointerUp}
          thumbSize={thumbSize}
        />
        <Input
          className="input"
          type="range"
          value={maxValue}
          min={min}
          max={max}
          step={step}
          onChange={handleMaxChange}
          onPointerUp={handlePointerUp}
          thumbSize={thumbSize}
        />
      </InputWrapper>

      <ControlWrapper thumbSize={thumbSize}>
        <Control thumbSize={thumbSize} style={{ left: `${minPos}%` }} />
        <Rail>
          <InnerRail style={{ left: `${minPos}%`, right: `${100 - maxPos}%` }} />
          {marks?.map((mark, index) => {
            const markValue = typeof mark === "number" ? mark : mark.value
            const markLabel = typeof mark === "number" ? null : mark.label
            const markClassName = typeof mark === "number" ? undefined : mark.className
            const markPos = ((markValue - min) / (max - min)) * 100
            return (
              <div key={index} style={{ position: "absolute", left: `${markPos}%`, top: "50%" }}>
                <Mark className={markClassName} />
                {markLabel && <Label>{markLabel}</Label>}
              </div>
            )
          })}
        </Rail>
        <Control thumbSize={thumbSize} style={{ left: `${maxPos}%` }} />
      </ControlWrapper>
    </Wrapper>
  )
}

export { RangeSlider }
