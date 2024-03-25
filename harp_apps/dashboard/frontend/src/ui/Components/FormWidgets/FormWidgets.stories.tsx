import { Radio } from "./Radio"
import { Checkbox } from "./Checkbox"

const data = [
  { name: "john", label: "John Coltrane" },
  { name: "miles", label: "Miles Davis" },
  { name: "bill", label: "Bill Evans" },
  { name: "louis", label: "Louis Armstrong" },
  { name: "ella", label: "Ella Fitzgerald" },
  { name: "billy", label: "Billy Holiday" },
  { name: "duke", label: "Duke Ellington" },
  { name: "charlie", label: "Charlie Parker" },
  { name: "dizzy", label: "Dizzy Gillespie" },
  { name: "thelonious", label: "Thelonious Monk" },
].sort((a, b) => a.label.localeCompare(b.label))

export const Radios = () => (
  <>
    {data.map((value) => (
      <Radio
        name={value.name}
        label={value.label}
        key={value.name}
        inputProps={{ defaultChecked: value.name === "duke" }}
      />
    ))}
  </>
)

const checkedData = new Set(["john", "bill"])

export const Checkboxes = () => (
  <>
    {data.map((value) => (
      <Checkbox name={value.name} label={value.label} key={value.name} defaultChecked={checkedData.has(value.name)} />
    ))}
  </>
)

const colors = ["text-red-500", "text-green-500", "text-blue-500", "text-yellow-500", "text-purple-500"]
const ringColors = ["ring-red-500", "ring-green-500", "ring-blue-500", "ring-yellow-500", "ring-purple-500"]

export const CheckboxesWithStyle = () => (
  <>
    {data.map((value, index) => (
      <Checkbox
        id={value.name}
        name={value.name}
        label={value.label}
        key={value.name}
        defaultChecked={checkedData.has(value.name)}
        className={ringColors[index % ringColors.length] + " ring-2 "}
        labelProps={{
          className: colors[index % colors.length],
        }}
        containerProps={{
          className: "ring-2 rounded-md p-2 m-2 " + ringColors[index % ringColors.length],
        }}
      />
    ))}
  </>
)
