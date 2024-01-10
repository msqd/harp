import {Paginator} from "./Paginator"
import {Pane} from "../Pane"
import {useState} from "react"

export const Default = () => {
    const [page, setPage] = useState(1)
    const props = {
        current: page,
        total: 273,
        setPage: (page: number) => setPage(page),
    }
    return (
        <Pane>
            <Paginator className="border-b" {...props} />
            <Pane hasDefaultBorder={false}>Hello, world.</Pane>
            <Paginator className="border-t" {...props} />
        </Pane>
    )
}
