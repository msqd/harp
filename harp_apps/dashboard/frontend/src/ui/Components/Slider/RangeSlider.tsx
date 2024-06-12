import { useEffect, useState } from "react"
import tw, { styled, css } from "twin.macro"

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
    margin: 40px calc(${thumbSize} / 2);
    padding-top: 1.6rem;
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

const RangeSlider = ({
  min = 0,
  max = 100,
  value,
  step = 1,
  onChange,
  thumbSize = "16px",
}: {
  min?: number
  max?: number
  value?: { min: number; max: number }
  step?: number
  onChange: (value: { min: number; max: number }) => void
  thumbSize?: string
}) => {
  const [minValue, setMinValue] = useState(value ? value.min : min)
  const [maxValue, setMaxValue] = useState(value ? value.max : max)

  useEffect(() => {
    if (value) {
      setMinValue(value.min)
      setMaxValue(value.max)
    }
  }, [value])

  const handleMinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    const newMinVal = Math.min(Number(e.target.value), maxValue - step)
    if (!value) setMinValue(newMinVal)
    onChange({ min: newMinVal, max: maxValue })
  }

  const handleMaxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    const newMaxVal = Math.max(Number(e.target.value), minValue + step)
    if (!value) setMaxValue(newMaxVal)
    onChange({ min: minValue, max: newMaxVal })
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
          thumbSize={thumbSize}
        />
      </InputWrapper>

      <ControlWrapper thumbSize={thumbSize}>
        <Control thumbSize={thumbSize} style={{ left: `${minPos}%` }} />
        <Rail>
          <InnerRail style={{ left: `${minPos}%`, right: `${100 - maxPos}%` }} />
        </Rail>
        <Control thumbSize={thumbSize} style={{ left: `${maxPos}%` }} />
      </ControlWrapper>
    </Wrapper>
  )
}

export { RangeSlider }
