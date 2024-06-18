import {
  ArrowPathIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
  LinkIcon,
  XMarkIcon,
} from "@heroicons/react/16/solid"
import { ArrowDownIcon, ArrowUpIcon } from "@heroicons/react/24/outline"
import { HTMLAttributes } from "react"
import { Link } from "react-router-dom"
import tw, { styled } from "twin.macro"

interface ButtonProps {
  onClick?: () => unknown
}

const StyledButton = styled.button`
  ${tw`text-gray-400 mx-1 font-medium text-xs`}

  > svg {
    ${tw`h-3 w-3 inline-block`}
  }
`

export function VerticalFiltersShowButton({ onClick }: ButtonProps) {
  return (
    <StyledButton onClick={onClick}>
      <ChevronDoubleRightIcon />
      <div className="w-4">
        <div className="rotate-90">filters</div>
      </div>
    </StyledButton>
  )
}

export function FiltersHideButton({ onClick }: ButtonProps) {
  return (
    <StyledButton onClick={onClick}>
      <ChevronDoubleLeftIcon /> hide
    </StyledButton>
  )
}

export function FiltersResetButton({ onClick }: ButtonProps) {
  return (
    <StyledButton onClick={onClick}>
      <ArrowPathIcon /> reset
    </StyledButton>
  )
}

export function DetailsCloseButton({ onClick, ...moreProps }: ButtonProps & HTMLAttributes<HTMLButtonElement>) {
  return (
    <StyledButton onClick={onClick} {...moreProps}>
      <XMarkIcon /> close
    </StyledButton>
  )
}

export function PreviousButton({ onClick }: ButtonProps) {
  return (
    <StyledButton onClick={onClick}>
      <ArrowUpIcon /> previous
    </StyledButton>
  )
}

export function NextButton({ onClick }: ButtonProps) {
  return (
    <StyledButton onClick={onClick}>
      <ArrowDownIcon /> next
    </StyledButton>
  )
}

export function RefreshButton({ onClick, ...moreProps }: ButtonProps & HTMLAttributes<HTMLButtonElement>) {
  return (
    <StyledButton onClick={onClick} {...moreProps}>
      <ArrowPathIcon />
    </StyledButton>
  )
}

export function OpenInNewWindowLink({ id }: { id: string }) {
  return (
    <StyledButton as={(props) => <Link {...props} target="_blank" to={`/transactions/${id}`} />}>
      <LinkIcon /> open in new window
    </StyledButton>
  )
}
